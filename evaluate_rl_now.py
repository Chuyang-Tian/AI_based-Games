from __future__ import annotations
import os, sys, math, random, argparse
from deidei_env import (
    PlayerState, Move, Outcome, ALL_MOVES, list_legal_moves, simulate_turn,
    choose_easy_move, LocalGTOSolver,
)
try:
    from gui_deidei import MOVE_NAMES_CN as _MOVE_NAMES_CN
except ImportError:
    _MOVE_NAMES_CN = {m: m.name for m in ALL_MOVES}
from rl_ai import (
    model_available, debug_dump_strategy, set_rl_inference_threads,
    _load_model, _obs_and_mask, rl_strategy_distribution_core, NUM_MOVES,
    MOVE_TO_IDX,
)


def _play_game(policy_move_fn, baseline_move_fn, seed: int, max_turns=120) -> str:
    rng = random.Random(seed)
    s_self = PlayerState()
    s_opp = PlayerState()
    for t in range(max_turns):
        try:
            s_move = policy_move_fn(s_self, s_opp, rng)
        except Exception:
            legal = list_legal_moves(s_self, s_opp)
            s_move = legal[0] if legal else Move.Charge
        try:
            o_move = baseline_move_fn(s_opp, s_self, rng)
        except Exception:
            legal = list_legal_moves(s_opp, s_self)
            o_move = legal[0] if legal else Move.Charge
        tr = simulate_turn(s_self, s_opp, s_move, o_move)
        s_self = tr.nextP
        s_opp = tr.nextC
        if tr.outcome != Outcome.Continue:
            if tr.outcome == Outcome.PlayerWin:
                return "W"
            if tr.outcome == Outcome.CpuWin:
                return "L"
            return "D"
    if s_self.dd > s_opp.dd:
        return "W"
    if s_self.dd < s_opp.dd:
        return "L"
    return "D"


def _rl_move_creator(checkpoint_path=None, device="cpu", deterministic=False):
    from rl_ai import choose_rl_move
    def _fn(s_self, s_opp, rng):
        return choose_rl_move(s_self, s_opp, rng, checkpoint_path=checkpoint_path,
                              deterministic=deterministic, fallback_easy=True,
                              device=device)
    return _fn


def _easy_move_creator():
    def _fn(s_self, s_opp, rng):
        return choose_easy_move(s_self, s_opp, rng)
    return _fn


def _hard_move_creator(gamma=0.96, iterations=1500):
    solver = LocalGTOSolver(gamma=gamma, iterations=iterations)
    def _fn(s_self, s_opp, rng):
        return solver.choose_move_for_cpu(s_self, s_opp, rng)
    return _fn


def _evaluate(name, policy_fn, baseline_fn, episodes, seed_offset):
    W = L = D = 0
    for ep in range(episodes):
        r = _play_game(policy_fn, baseline_fn, seed=seed_offset + ep)
        if r == "W": W += 1
        elif r == "L": L += 1
        else: D += 1
    total = W + L + D
    return {"name": name, "W": W, "L": L, "D": D, "total": total,
            "wr": W/total, "lr": L/total, "dr": D/total}


def _entropy_report(checkpoint_path=None, topk=8):
    lines = []
    lines.append("=== 6 种典型局面策略熵 & 首招 Top-%d ===" % topk)
    from deidei_env import kDDOne
    scenarios = [
        ("开局 0-0",              PlayerState(),                                   PlayerState()),
        ("我方领先 5DD vs 0",     PlayerState(dd=5*kDDOne),                         PlayerState(dd=0)),
        ("我方落后 0 vs 5DD",     PlayerState(dd=0),                                 PlayerState(dd=5*kDDOne)),
        ("炸药 2 层",            PlayerState(bombLayers=2, dd=0),                    PlayerState(dd=6)),
        ("雷电 3 层",            PlayerState(lightning=3, dd=0),                     PlayerState(dd=6)),
        ("聂湘4充 + 距喦",        PlayerState(nxCharge=4, juyanBuff=True, dd=6),      PlayerState(dd=12)),
    ]
    ok = model_available(checkpoint_path)
    if not ok:
        lines.append("(无模型，跳过)")
        return "\n".join(lines)
    for name, ss, os_ in scenarios:
        lines.append("\n[%s]" % name)
        lines.append(debug_dump_strategy(ss, os_, label="", top_k=topk,
                                         checkpoint_path=checkpoint_path))
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="立刻评估当前 latest.zip 模型：胜率 + 策略熵（不用等 save_interval）")
    p.add_argument("--episodes", type=int, default=50)
    p.add_argument("--hard-episodes", type=int, default=20)
    p.add_argument("--seed", type=int, default=10000)
    p.add_argument("--threads", type=int, default=2,
                   help="评估时 RL 推理线程数（CPU 凉快点）")
    p.add_argument("--hard-iters", type=int, default=1200,
                   help="Hard/GTO 每步 regret 迭代数（越大越慢越准）")
    p.add_argument("--checkpoint", type=str, default=None,
                   help="指定模型路径；默认 rl_checkpoints/latest.zip")
    p.add_argument("--hard-only", action="store_true", help="只做策略熵打印（最快）")
    p.add_argument("--winrate-only", action="store_true", help="只做胜率评估（稍慢）")
    args = p.parse_args()

    set_rl_inference_threads(args.threads)

    if args.checkpoint:
        ckpt = args.checkpoint
    else:
        ckpt = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "rl_checkpoints", "latest.zip")

    print("=" * 68)
    print("评估 checkpoint:", ckpt)
    print("存在:", os.path.exists(ckpt), "   模型可用:", model_available(ckpt))
    if os.path.exists(ckpt):
        import datetime as _dt
        mtime = _dt.datetime.fromtimestamp(os.path.getmtime(ckpt))
        size_mb = os.path.getsize(ckpt) / 1024.0 / 1024.0
        print("修改时间:", mtime.strftime("%Y-%m-%d %H:%M:%S"),
              "  大小: %.2f MB" % size_mb)
    print("线程数:", args.threads)
    print("=" * 68)

    if not args.winrate_only:
        print()
        print(_entropy_report(ckpt, topk=8))
        print()

    if not args.hard_only:
        print("=" * 68)
        print("胜率评估 (%d 场 vs Easy / %d 场 vs Hard-iters=%d)"
              % (args.episodes, args.hard_episodes, args.hard_iters))
        print("-" * 68)

        policy = _rl_move_creator(ckpt, device="cpu", deterministic=False)
        easy = _easy_move_creator()
        hard = _hard_move_creator(gamma=0.96, iterations=args.hard_iters)

        r_easy = _evaluate("vs Easy", policy, easy, args.episodes, args.seed)
        print("%-14s  胜 %2d/%-2d  %5.1f%%   败 %2d/%-2d  %5.1f%%   平 %2d  %5.1f%%" % (
            r_easy["name"], r_easy["W"], r_easy["total"], r_easy["wr"]*100,
            r_easy["L"], r_easy["total"], r_easy["lr"]*100,
            r_easy["D"], r_easy["dr"]*100))
        sys.stdout.flush()

        r_hard = _evaluate("vs Hard", policy, hard, args.hard_episodes, args.seed + 50000)
        print("%-14s  胜 %2d/%-2d  %5.1f%%   败 %2d/%-2d  %5.1f%%   平 %2d  %5.1f%%" % (
            r_hard["name"], r_hard["W"], r_hard["total"], r_hard["wr"]*100,
            r_hard["L"], r_hard["total"], r_hard["lr"]*100,
            r_hard["D"], r_hard["dr"]*100))
        print("=" * 68)

        wr_easy = r_easy["wr"]
        wr_hard = r_hard["wr"]
        print("\n[快速判读]")
        if wr_easy < 0.55:
            print("  vs Easy 胜率 < 55%：策略还很弱，对手池可能没切 → 建议立刻重训（用 --balanced --reset）")
        elif wr_easy < 0.8:
            print("  vs Easy 胜率 55~80%：还在学习中，可以再跑一会")
        else:
            print("  vs Easy 胜率 > 80%：打 Easy 已很稳")
        if wr_hard < 0.4:
            print("  vs Hard 胜率 < 40%：对 Hard 策略差距还大（可能单峰/偏科）")
        elif wr_hard < 0.55:
            print("  vs Hard 胜率 40~55%：已经接近 Hard 水平，不错")
        else:
            print("  vs Hard 胜率 > 55%：RL 已经强于 GTO Hard（长期策略更好）")
    print()


if __name__ == "__main__":
    main()
