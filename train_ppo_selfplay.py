from __future__ import annotations
import os
import sys
import glob
import random
import copy
import pickle
from typing import List, Callable, Optional, Any, Dict
from dataclasses import dataclass
import numpy as np

try:
    import torch
except ImportError:
    print("[ERROR] torch 未安装，请先 pip install torch 或安装 requirements_rl.txt")
    sys.exit(1)

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize, DummyVecEnv
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker
    from sb3_contrib.common.maskable.evaluation import evaluate_policy as mask_evaluate_policy
    HAS_MASKABLE = True
except ImportError:
    HAS_MASKABLE = False
    print("[WARN] sb3_contrib 未安装，将退化为普通 PPO（无动作 mask，建议 pip install sb3-contrib）")
    from stable_baselines3 import PPO

from deidei_env import (
    PlayerState, Move, ALL_MOVES, list_legal_moves, simulate_turn, Outcome,
    choose_easy_move, LocalGTOSolver,
)
from deidei_gym_env import DeiDeiSelfPlayEnv, NUM_MOVES, ALL_MOVES as ENV_ALL_MOVES, MOVE_TO_IDX


CHECKPOINT_DIR = "./rl_checkpoints"
TB_LOG_DIR = "./rl_tensorboard"
OPPONENT_POOL_FILE = os.path.join(CHECKPOINT_DIR, "opponent_pool.pkl")


def set_cpu_limits(num_threads: int, quiet: bool = False):
    if num_threads is not None and num_threads > 0:
        try:
            torch.set_num_threads(num_threads)
        except Exception:
            pass
        try:
            torch.set_num_interop_threads(max(1, min(4, num_threads)))
        except Exception:
            pass
        for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                  "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                  "BLIS_NUM_THREADS"):
            os.environ[k] = str(num_threads)
        if not quiet:
            print(f"[CPU] torch threads={num_threads}  &  BLAS/OpenMP 限 {num_threads} 线程")


def ensure_dirs():
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(TB_LOG_DIR, exist_ok=True)


def mask_fn(env) -> np.ndarray:
    if hasattr(env, "unwrapped") and isinstance(env.unwrapped, DeiDeiSelfPlayEnv):
        core = env.unwrapped
        from deidei_gym_env import _legal_mask_fast
        return _legal_mask_fast(core.self_state, core.opp_state).astype(bool)
    return np.ones(NUM_MOVES, dtype=bool)


def make_env(opponent_fn=None, opponent_payload=None, use_mask=True, rank=0, seed=0,
             reward_shaping: bool = True):
    def _init():
        env = DeiDeiSelfPlayEnv(opponent_fn=opponent_fn, opponent_payload=opponent_payload,
                                max_turns=120, reward_shaping=reward_shaping,
                                use_buffers=True)
        if HAS_MASKABLE and use_mask:
            env = ActionMasker(env, mask_fn)
        env.reset(seed=seed + rank)
        return env
    return _init


@dataclass
class OpponentEntry:
    name: str
    type: str
    checkpoint_path: Optional[str] = None
    payload: Optional[Any] = None


class OpponentPool:
    def __init__(self):
        self.entries: List[OpponentEntry] = []

    def add(self, entry: OpponentEntry):
        self.entries.append(entry)

    def sample(self, rng: random.Random, latest_checkpoint_path: Optional[str] = None,
               latest_ratio: float = 0.4) -> OpponentEntry:
        if (not self.entries) and (latest_checkpoint_path is None):
            return OpponentEntry("easy", "heuristic")
        use_latest = (latest_checkpoint_path is not None) and (rng.random() < latest_ratio)
        if use_latest:
            return OpponentEntry("latest", "model", checkpoint_path=latest_checkpoint_path)
        return rng.choice(self.entries)

    def save(self, path=OPPONENT_POOL_FILE):
        with open(path, "wb") as f:
            pickle.dump(self.entries, f)

    def load(self, path=OPPONENT_POOL_FILE):
        if os.path.exists(path):
            with open(path, "rb") as f:
                self.entries = pickle.load(f)


def build_opponent_fn(entry: OpponentEntry, rng: random.Random) -> Callable:
    if entry.type == "heuristic":
        if entry.name == "gto_hard":
            solver = LocalGTOSolver(gamma=0.96, iterations=1500)
            def _fn(opp_s, self_s, payload=None):
                return solver.choose_move_for_cpu(self_s, opp_s, rng)
            return _fn
        else:
            def _fn(opp_s, self_s, payload=None):
                return choose_easy_move(opp_s, self_s, rng)
            return _fn
    elif entry.type == "model":
        path = entry.checkpoint_path
        if path is None or not os.path.exists(path):
            def _fn(opp_s, self_s, payload=None):
                return choose_easy_move(opp_s, self_s, rng)
            return _fn
        try:
            if HAS_MASKABLE:
                model = MaskablePPO.load(path, device="cpu")
            else:
                model = PPO.load(path, device="cpu")
        except Exception as e:
            print(f"[WARN] 加载对手模型失败 {path}: {e}，退回 Easy")
            def _fn(opp_s, self_s, payload=None):
                return choose_easy_move(opp_s, self_s, rng)
            return _fn

        def predict_move_from_model(opp_s: PlayerState, self_s: PlayerState, payload=None):
            from deidei_gym_env import _concat_obs, _legal_mask
            obs = _concat_obs(self_s, opp_s)
            mask = _legal_mask(self_s, opp_s).astype(bool)
            if HAS_MASKABLE:
                try:
                    action, _ = model.predict(obs, deterministic=False, action_masks=mask)
                except Exception:
                    action, _ = model.predict(obs, deterministic=False)
            else:
                action, _ = model.predict(obs, deterministic=False)
            if 0 <= int(action) < NUM_MOVES and mask[int(action)]:
                return ALL_MOVES[int(action)]
            legal = [m for m in ALL_MOVES if mask[MOVE_TO_IDX.get(m, 0)]]
            if legal:
                return rng.choice(legal)
            return Move.Charge
        return predict_move_from_model
    else:
        def _fn(opp_s, self_s, payload=None):
            return choose_easy_move(opp_s, self_s, rng)
        return _fn


def evaluate_vs_baseline(model_path: str, baseline: str = "easy",
                         episodes: int = 100, seed: int = 42) -> Dict[str, float]:
    rng = random.Random(seed)
    entry = OpponentEntry(baseline, "heuristic")
    opp_fn = build_opponent_fn(entry, rng)
    if HAS_MASKABLE:
        model = MaskablePPO.load(model_path, device="cpu")
    else:
        model = PPO.load(model_path, device="cpu")

    wins = losses = draws = 0
    for ep in range(episodes):
        s_self = PlayerState()
        s_opp = PlayerState()
        done = False
        for t in range(120):
            from deidei_gym_env import _concat_obs, _legal_mask
            obs = _concat_obs(s_self, s_opp)
            mask = _legal_mask(s_self, s_opp).astype(bool)
            if HAS_MASKABLE:
                try:
                    action, _ = model.predict(obs, deterministic=False, action_masks=mask)
                except Exception:
                    action, _ = model.predict(obs, deterministic=False)
            else:
                action, _ = model.predict(obs, deterministic=False)
            a = int(action)
            if 0 <= a < NUM_MOVES and mask[a]:
                s_move = ALL_MOVES[a]
            else:
                legal = [m for m in ALL_MOVES if mask[MOVE_TO_IDX.get(m, 0)]]
                s_move = (rng.choice(legal) if legal else Move.Charge)
            o_move = opp_fn(s_opp, s_self)
            tr = simulate_turn(s_self, s_opp, s_move, o_move)
            s_self = tr.nextP
            s_opp = tr.nextC
            if tr.outcome != Outcome.Continue:
                if tr.outcome == Outcome.PlayerWin:
                    wins += 1
                elif tr.outcome == Outcome.CpuWin:
                    losses += 1
                else:
                    draws += 1
                done = True
                break
        if not done:
            if s_self.dd > s_opp.dd:
                wins += 1
            elif s_self.dd < s_opp.dd:
                losses += 1
            else:
                draws += 1
    total = wins + losses + draws
    return {
        "win_rate": wins / total,
        "loss_rate": losses / total,
        "draw_rate": draws / total,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "total": total,
    }


class SelfPlayUpdateCallback(BaseCallback):
    def __init__(self, pool: OpponentPool, trainer_rng: random.Random,
                 save_interval_steps: int = 50000,
                 eval_episodes: int = 60,
                 latest_ratio: float = 0.35,
                 verbose: int = 0):
        super().__init__(verbose)
        self.pool = pool
        self.rng = trainer_rng
        self.save_interval = save_interval_steps
        self.eval_episodes = eval_episodes
        self.latest_ratio = latest_ratio
        self._last_saved_step = 0

    def _swap_opponent(self):
        latest_path = os.path.join(CHECKPOINT_DIR, "latest.zip")
        if os.path.exists(latest_path):
            latest = latest_path
        else:
            latest = None
        entry = self.pool.sample(self.rng, latest_checkpoint_path=latest, latest_ratio=self.latest_ratio)
        new_opp = build_opponent_fn(entry, self.rng)
        venv = self.training_env
        try:
            n_envs = venv.num_envs
        except Exception:
            n_envs = 1
        if self.verbose:
            print(f"  [SwapOpponent] 选对手: type={entry.type}  name={entry.name}")
        for i in range(n_envs):
            target = None
            try:
                envs_i = getattr(venv, "envs", None)
                if envs_i is not None and i < len(envs_i):
                    cur = envs_i[i]
                    for _ in range(10):
                        if isinstance(cur, DeiDeiSelfPlayEnv):
                            target = cur; break
                        nxt = getattr(cur, "env", None) or getattr(cur, "venv", None)
                        if nxt is None or nxt is cur:
                            break
                        cur = nxt
                if target is None:
                    try:
                        unwrapped = venv.get_attr("unwrapped", indices=[i])[0]
                        if isinstance(unwrapped, DeiDeiSelfPlayEnv):
                            target = unwrapped
                    except Exception:
                        pass
            except Exception:
                target = None
            if target is not None:
                target.opponent_fn = new_opp
                target.opponent_payload = None
            else:
                try:
                    venv.set_attr("opponent_fn", new_opp, indices=[i])
                except Exception:
                    pass

    def _on_step(self) -> bool:
        if self.n_calls - self._last_saved_step >= self.save_interval:
            self._last_saved_step = self.n_calls
            self._save_and_eval()
            self._swap_opponent()
        return True

    def _save_and_eval(self):
        ensure_dirs()
        step = self.num_timesteps
        tag_path = os.path.join(CHECKPOINT_DIR, f"model_step{step}.zip")
        latest_path = os.path.join(CHECKPOINT_DIR, "latest.zip")
        self.model.save(tag_path)
        self.model.save(latest_path)
        if self.verbose:
            print(f"\n[SelfPlay] step={step} 保存 checkpoint: {tag_path}")
        try:
            if self.eval_episodes > 0:
                r_easy = evaluate_vs_baseline(latest_path, "easy", episodes=self.eval_episodes,
                                              seed=1000 + step % 100000)
                print(f"  vs Easy  胜率={r_easy['win_rate']:.2%} 败率={r_easy['loss_rate']:.2%} 平={r_easy['draw_rate']:.2%}  (N={r_easy['total']})")
                if step >= 100000:
                    r_hard = evaluate_vs_baseline(latest_path, "gto_hard", episodes=max(20, self.eval_episodes // 3),
                                                  seed=2000 + step % 100000)
                    print(f"  vs Hard  胜率={r_hard['win_rate']:.2%} 败率={r_hard['loss_rate']:.2%} 平={r_hard['draw_rate']:.2%}")
        except Exception as e:
            print(f"  [评估异常] {e}")
        entry = OpponentEntry(f"model_{step}", "model", checkpoint_path=tag_path)
        self.pool.add(entry)
        if len(self.pool.entries) > 20:
            self.pool.entries = self.pool.entries[-20:]
        self.pool.save()


def main(total_timesteps: int = 500_000,
         n_envs: int = 4,
         seed: int = 42,
         save_interval_steps: int = 40_000,
         eval_episodes: int = 50,
         latest_ratio: float = 0.25,
         ent_coef: float = 0.06,
         lr: float = 2.5e-4,
         num_threads: Optional[int] = None,
         batch_size: Optional[int] = None,
         n_steps: Optional[int] = None,
         n_epochs: Optional[int] = None,
         device: str = "auto",
         reward_shaping: bool = True,
         verbose: bool = True):
    if num_threads is not None:
        set_cpu_limits(num_threads, quiet=not verbose)
    elif verbose:
        try:
            cur_t = torch.get_num_threads()
        except Exception:
            cur_t = None
        if cur_t is not None and cur_t > 4:
            print(f"[CPU] 当前 torch threads={cur_t} (默认). 如需降低CPU占用可加 --num-threads 2 或 --low-cpu")

    ensure_dirs()
    trainer_rng = random.Random(seed)
    pool = OpponentPool()
    pool.load()
    if not pool.entries:
        pool.add(OpponentEntry("easy", "heuristic"))
        pool.add(OpponentEntry("gto_hard", "heuristic"))
        pool.save()
        if verbose:
            print("[SelfPlay] 初始化对手池：Easy + GTO Hard")
    else:
        if verbose:
            print(f"[SelfPlay] 加载对手池，历史 {len(pool.entries)} 个对手")

    if batch_size is None:
        batch_size = 128 if n_envs >= 4 else 64
    if n_steps is None:
        n_steps = 2048 if n_envs >= 4 else 1024
    if n_epochs is None:
        n_epochs = 10 if n_envs >= 4 else 6

    latest_path = os.path.join(CHECKPOINT_DIR, "latest.zip")
    initial_entry = pool.sample(trainer_rng, latest_checkpoint_path=(latest_path if os.path.exists(latest_path) else None),
                                latest_ratio=latest_ratio)
    initial_opp = build_opponent_fn(initial_entry, trainer_rng)
    if verbose:
        print(f"[SelfPlay] 初始对手: type={initial_entry.type}  name={initial_entry.name}")

    if HAS_MASKABLE:
        env_fns = [make_env(opponent_fn=initial_opp, opponent_payload=None, use_mask=True,
                            rank=i, seed=seed, reward_shaping=reward_shaping)
                   for i in range(n_envs)]
        env = DummyVecEnv(env_fns)
    else:
        env_fns = [make_env(opponent_fn=initial_opp, opponent_payload=None, use_mask=False,
                            rank=i, seed=seed, reward_shaping=reward_shaping)
                   for i in range(n_envs)]
        env = DummyVecEnv(env_fns)

    continue_from = latest_path if os.path.exists(latest_path) else None
    if continue_from and HAS_MASKABLE:
        if verbose:
            print(f"[SelfPlay] 继续训练：{continue_from}")
        model = MaskablePPO.load(continue_from, env=env, device=device,
                                 tensorboard_log=TB_LOG_DIR, learning_rate=lr, ent_coef=ent_coef)
    elif continue_from:
        if verbose:
            print(f"[SelfPlay] 继续训练：{continue_from}")
        model = PPO.load(continue_from, env=env, device=device,
                         tensorboard_log=TB_LOG_DIR, learning_rate=lr, ent_coef=ent_coef)
    else:
        if verbose:
            print("[SelfPlay] 从头训练新策略")
        policy_kwargs = dict(net_arch=[256, 256])
        common_args = dict(
            policy="MlpPolicy",
            env=env,
            learning_rate=lr,
            n_steps=n_steps,
            batch_size=batch_size,
            n_epochs=n_epochs,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=ent_coef,
            vf_coef=0.5,
            max_grad_norm=0.5,
            verbose=1 if verbose else 0,
            seed=seed,
            device=device,
            tensorboard_log=TB_LOG_DIR,
            policy_kwargs=policy_kwargs,
        )
        if HAS_MASKABLE:
            model = MaskablePPO(**common_args)
        else:
            model = PPO(**common_args)
    if verbose:
        print(f"[SelfPlay] 超参: lr={lr:.1e}  ent_coef={ent_coef:.3f}  latest_ratio={latest_ratio:.2f}")
        print(f"           n_envs={n_envs}  n_steps={n_steps}  batch={batch_size}  epochs={n_epochs}  device={device}")

    cb = SelfPlayUpdateCallback(
        pool=pool,
        trainer_rng=trainer_rng,
        save_interval_steps=save_interval_steps,
        eval_episodes=eval_episodes,
        latest_ratio=latest_ratio,
        verbose=1 if verbose else 0,
    )

    try:
        model.learn(total_timesteps=total_timesteps, callback=cb, tb_log_name="deidei_ppo",
                    reset_num_timesteps=(continue_from is None))
    except KeyboardInterrupt:
        if verbose:
            print("\n[SelfPlay] 训练被中断，保存当前模型...")
    finally:
        ensure_dirs()
        tag = model.num_timesteps
        final_path = os.path.join(CHECKPOINT_DIR, f"model_step{tag}.zip")
        latest = os.path.join(CHECKPOINT_DIR, "latest.zip")
        model.save(final_path)
        model.save(latest)
        pool.save()
        if verbose:
            print(f"[SelfPlay] 已保存：{final_path} / {latest}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DeiDei PPO Self-Play 训练")
    parser.add_argument("--timesteps", type=int, default=500_000, help="总训练步数")
    parser.add_argument("--envs", type=int, default=4, help="并行环境数（DummyVecEnv 多进程；越多越吃 CPU）")
    parser.add_argument("--save-interval", type=int, default=40_000, help="保存评估间隔（步数）")
    parser.add_argument("--eval-episodes", type=int, default=50, help="每次评估局数（越大越吃 CPU）")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--ent-coef", type=float, default=0.06, help="entropy 正则系数（越大越探索，推荐 0.04~0.1）")
    parser.add_argument("--lr", type=float, default=2.5e-4, help="学习率")
    parser.add_argument("--latest-ratio", type=float, default=0.25, help="对手池采样最新版比例（其余=历史版本+Easy+Hard）")
    parser.add_argument("--reset", action="store_true", help="删除 rl_checkpoints 内的历史模型与对手池，重新开始训练")
    parser.add_argument("--num-threads", type=int, default=None,
                        help="torch+OpenMP/MKL 线程数上限；不设则用 torch 默认（通常=CPU 逻辑核数，非常高）")
    parser.add_argument("--batch-size", type=int, default=None, help="PPO batch size；默认随 envs 自动")
    parser.add_argument("--n-steps", type=int, default=None, help="PPO rollout 长度；默认随 envs 自动")
    parser.add_argument("--n-epochs", type=int, default=None, help="PPO epoch；默认随 envs 自动")
    parser.add_argument("--device", type=str, default="cpu",
                        help='推理/训练设备；默认 "cpu"（纯 CPU 训练更稳），可 "cuda" / "mps" / "auto"')
    parser.add_argument("--no-reward-shaping", action="store_true", help="关掉 DD 差小奖励塑形")
    parser.add_argument("--low-cpu", action="store_true",
                        help='一键"省电档": threads=2, envs=2, batch=32, n-steps=1024, n-epochs=4, eval=15')
    parser.add_argument("--balanced", action="store_true",
                        help='一键"平衡档": threads=4, envs=3, batch=64, n-steps=1536, n-epochs=6, eval=25')
    parser.add_argument("--max-cpu", action="store_true",
                        help='一键"极速档": threads=min(16,逻辑核), envs=6, batch=256, n-steps=2048, n-epochs=12, eval=60')
    args = parser.parse_args()

    if args.low_cpu:
        args.num_threads = args.num_threads or 2
        args.envs = 2
        args.batch_size = args.batch_size or 32
        args.n_steps = args.n_steps or 1024
        args.n_epochs = args.n_epochs or 4
        args.eval_episodes = min(args.eval_episodes, 15)
    elif args.balanced:
        args.num_threads = args.num_threads or 4
        args.envs = min(args.envs, 3)
        args.batch_size = args.batch_size or 64
        args.n_steps = args.n_steps or 1536
        args.n_epochs = args.n_epochs or 6
        args.eval_episodes = min(args.eval_episodes, 25)
    elif args.max_cpu:
        try:
            import multiprocessing as _mp
            args.num_threads = args.num_threads or min(16, max(4, _mp.cpu_count() or 4))
        except Exception:
            args.num_threads = args.num_threads or 8
        args.envs = max(args.envs, 6)
        args.batch_size = args.batch_size or 256
        args.n_steps = args.n_steps or 2048
        args.n_epochs = args.n_epochs or 12
        args.eval_episodes = max(args.eval_episodes, 60)

    if args.reset:
        import shutil
        if os.path.exists(CHECKPOINT_DIR):
            for f in glob.glob(os.path.join(CHECKPOINT_DIR, "model_*.zip")):
                try: os.remove(f)
                except: pass
            for f in [os.path.join(CHECKPOINT_DIR, "latest.zip"),
                      OPPONENT_POOL_FILE]:
                if os.path.exists(f):
                    try: os.remove(f)
                    except: pass
        print("[SelfPlay] --reset 已清空旧 checkpoint")

    main(
        total_timesteps=args.timesteps,
        n_envs=args.envs,
        seed=args.seed,
        save_interval_steps=args.save_interval,
        eval_episodes=args.eval_episodes,
        latest_ratio=args.latest_ratio,
        ent_coef=args.ent_coef,
        lr=args.lr,
        num_threads=args.num_threads,
        batch_size=args.batch_size,
        n_steps=args.n_steps,
        n_epochs=args.n_epochs,
        device=args.device,
        reward_shaping=(not args.no_reward_shaping),
        verbose=True,
    )
