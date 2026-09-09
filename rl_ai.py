from __future__ import annotations
import os
import math
import random as _random_mod
from typing import Optional, Tuple, Dict, Any, List

from deidei_env import (
    PlayerState, Move, list_legal_moves, choose_easy_move, kDDOne,
    is_attack_move, is_unreflectable,
)
try:
    from gui_deidei import MOVE_NAMES_CN
except ImportError:
    MOVE_NAMES_CN = {m: m.name for m in Move}
from deidei_gym_env import (
    _concat_obs, _legal_mask_fast, NUM_MOVES, ALL_MOVES, MOVE_TO_IDX,
)

DEFAULT_CHECKPOINT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "rl_checkpoints", "latest.zip")

_MODEL_CACHE: Dict[str, Tuple[Any, bool]] = {}

_has_maskable = None

_RL_THREADS_OVERRIDE: Optional[int] = None


def set_rl_inference_threads(n: Optional[int]) -> None:
    global _RL_THREADS_OVERRIDE
    _RL_THREADS_OVERRIDE = n


def get_rl_inference_threads() -> Optional[int]:
    return _RL_THREADS_OVERRIDE


def _check_maskable() -> bool:
    global _has_maskable
    if _has_maskable is not None:
        return _has_maskable
    try:
        from sb3_contrib import MaskablePPO
        _has_maskable = True
    except ImportError:
        _has_maskable = False
    return _has_maskable


def _apply_inference_thread_setting():
    import os as _os
    try:
        import torch as _torch
        if _RL_THREADS_OVERRIDE is not None:
            try:
                _torch.set_num_threads(max(1, int(_RL_THREADS_OVERRIDE)))
            except Exception:
                pass
            try:
                _torch.set_num_interop_threads(max(1, min(2, int(_RL_THREADS_OVERRIDE))))
            except Exception:
                pass
            limit = str(max(1, int(_RL_THREADS_OVERRIDE)))
            for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                      "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS"):
                _os.environ[k] = limit
    except Exception:
        pass


def _load_model(checkpoint_path: Optional[str] = None,
                device: str = "cpu"):
    path = checkpoint_path or DEFAULT_CHECKPOINT
    cache_key = f"{path}:::{device}:::{_RL_THREADS_OVERRIDE}"
    if cache_key in _MODEL_CACHE:
        _apply_inference_thread_setting()
        return _MODEL_CACHE[cache_key]
    if not os.path.exists(path):
        _MODEL_CACHE[cache_key] = (None, _check_maskable())
        _apply_inference_thread_setting()
        return None, _check_maskable()
    _apply_inference_thread_setting()
    try:
        if _check_maskable():
            from sb3_contrib import MaskablePPO
            model = MaskablePPO.load(path, device=device)
        else:
            from stable_baselines3 import PPO
            model = PPO.load(path, device=device)
        _MODEL_CACHE[cache_key] = (model, _check_maskable())
        return model, _check_maskable()
    except Exception as e:
        print(f"[RL AI] 加载模型失败 {path}: {e}，退回 Easy 启发式")
        _MODEL_CACHE[cache_key] = (None, _check_maskable())
        return None, _check_maskable()


def model_available(checkpoint_path: Optional[str] = None) -> bool:
    m, _ = _load_model(checkpoint_path)
    return m is not None


def _fallback_distribution(legal_moves) -> Tuple[List[Move], List[float]]:
    if not legal_moves:
        return [], []
    n = len(legal_moves)
    return legal_moves, [1.0 / n] * n


import numpy as _np

_obs_buf = None
_mask_buf = None


def _obs_and_mask(cpu_state, player_state):
    global _obs_buf, _mask_buf
    from deidei_gym_env import OBS_DIM
    if _obs_buf is None:
        _obs_buf = _np.zeros(OBS_DIM, dtype=_np.float32)
        _mask_buf = _np.zeros(NUM_MOVES, dtype=_np.int8)
    obs = _concat_obs(cpu_state, player_state, out=_obs_buf)
    mask = _legal_mask_fast(cpu_state, player_state, out=_mask_buf)
    return obs, mask.astype(bool)


def choose_rl_move(cpu_state: PlayerState,
                   player_state: PlayerState,
                   rng: Optional[_random_mod.Random] = None,
                   checkpoint_path: Optional[str] = None,
                   deterministic: bool = False,
                   fallback_easy: bool = True,
                   sample_from_distribution: bool = True,
                   device: str = "cpu") -> Move:
    if rng is None:
        rng = _random_mod.Random()
    model, has_mask = _load_model(checkpoint_path, device=device)
    legal_moves = list_legal_moves(cpu_state, player_state)

    if model is None:
        if fallback_easy:
            return choose_easy_move(cpu_state, player_state, rng)
        if not legal_moves:
            return Move.Charge
        return rng.choice(legal_moves)

    obs, mask = _obs_and_mask(cpu_state, player_state)

    if (not deterministic) and sample_from_distribution:
        moves, probs = rl_strategy_distribution_core(
            model, has_mask, cpu_state, player_state, obs, mask, legal_moves
        )
        if moves and probs and sum(probs) > 1e-9:
            u = rng.random() * sum(probs)
            acc = 0.0
            for mv, pr in zip(moves, probs):
                acc += pr
                if u <= acc:
                    return mv

    try:
        if has_mask:
            action, _ = model.predict(obs, deterministic=deterministic, action_masks=mask)
        else:
            action, _ = model.predict(obs, deterministic=deterministic)
    except Exception:
        if fallback_easy:
            return choose_easy_move(cpu_state, player_state, rng)
        return (rng.choice(legal_moves) if legal_moves else Move.Charge)
    a = int(action)
    if 0 <= a < NUM_MOVES and mask[a]:
        return ALL_MOVES[a]
    if not legal_moves:
        return Move.Charge
    if fallback_easy:
        return choose_easy_move(cpu_state, player_state, rng)
    return rng.choice(legal_moves)


def _apply_expert_heuristic_filter(cpu_state: PlayerState,  # RL 自己的状态（= list_legal_moves 第一个参数=自己
                                   player_state: PlayerState,  # 对手的状态（= list_legal_moves 第二个参数=对手
                                   moves: List[Move],
                                   probs: List[float]) -> Tuple[List[Move], List[float]]:
    if not moves:
        return moves, probs
    rl_self = cpu_state          # RL 自己（CPU 难度：RL 自己的状态
    rl_opp = player_state      # 对手状态
    is_first_turn = (rl_self.lastMove == Move.NoMove
                     and rl_opp.lastMove == Move.NoMove
                     and rl_self.dd == 0
                     and rl_opp.dd == 0)
    BANNED_ON_FIRST_TURN = {
        Move.Def, Move.PragonDef, Move.VolvoDef, Move.NieXiangDef,
        Move.ThreeDef, Move.JuYan, Move.Cloud, Move.TianLiJun,
        Move.LiQiang,
    }
    MY_DD_OK_LEAD = 5 * kDDOne  # 自己 - 对手 ≥ 5DD（大比分领先
    MY_DD_BEHIND = -5 * kDDOne
    banned_idxs = []
    for i, m in enumerate(moves):
        if is_first_turn and m in BANNED_ON_FIRST_TURN:
            banned_idxs.append(i)
            continue
        if m == Move.LiQiang:
            if rl_opp.lastMove == Move.NoMove:  # 对手上回合没出招，历强必不触发
                banned_idxs.append(i)
            continue
        if m == Move.ZhangXinWei:
            if (not rl_opp.hasHighAttackRecord) or rl_opp.zhangUsed:
                banned_idxs.append(i)
            continue
        dd_diff = rl_self.dd - rl_opp.dd
        if dd_diff >= MY_DD_OK_LEAD and m in {Move.Def, Move.VolvoDef, Move.PragonDef,
                                             Move.NieXiangDef, Move.ThreeDef, Move.JuYan}:
            banned_idxs.append(i)
            continue
        if dd_diff <= MY_DD_BEHIND and m == Move.Suicide:
            banned_idxs.append(i)
            continue
    # === 防御类「真·无任何独有价值 → 纯送回合 → ban」
    # blocks_attack 核心机制：
    #   Bi 只有 Def/TianLiJun/Bomb/JuYan 能挡！4 个专属防御(Volvo/Pragon/Three/NieXiangDef) 全挡不住 Bi！
    #   Xiao 普通版 全部 6 防御都能挡（包括 Def）
    # → 推论：4 个专属防御「有独有价值 ↔ 对手能出对应专属攻击（Def 挡不住的那种）」
    #         否则，把防御概率全让给 Def（既挡 Xiao 又挡 Bi，严格占优），4 个专属防御直接 ban
    # 详细规则：
    #   VolvoDef   独有价值 ↔ {Volvo, BombVolvo, BombFlipVolvo, FlipVolvo} 有一个合法
    #   PragonDef  独有价值 ↔ {Pragon, BombPragon} 有一个合法
    #   ThreeDef   独有价值 ↔ {Three, FreeThree, FreeRotateThree, RotateThree} 有一个合法
    #   NieXiangDef独有价值 ↔ {NieXiang} 合法 且 对手 nxCharge>=4
    #   Def        有价值 ↔ Xiao(2单位) 或 Bi(6单位) 能出 → dd<2 单位时没的挡才 ban
    #   JuYan      有额外下回合穿防 Xiao 收益 → 几乎永不 ban（仅首回合 BANNED_ON_FIRST_TURN 已处理）
    _opp_legal_cache = None
    def _opp_legal():
        nonlocal _opp_legal_cache
        if _opp_legal_cache is None:
            _opp_legal_cache = set(list_legal_moves(rl_opp, rl_self))
        return _opp_legal_cache
    _opp_dd = rl_opp.dd
    for i, m in enumerate(moves):
        if i in banned_idxs:
            continue
        if m == Move.VolvoDef:
            # 独有价值：只能挡 Volvo 类（+ Xiao 普通版，但 Def 也能挡 Xiao+Bi → 无 Volvo 类时 VolvoDef 纯亏）
            has_volvo = ((Move.Volvo in _opp_legal()) or (Move.BombVolvo in _opp_legal())
                         or (Move.BombFlipVolvo in _opp_legal()) or (Move.FlipVolvo in _opp_legal()))
            if not has_volvo:
                banned_idxs.append(i)
            continue
        if m == Move.PragonDef:
            # 独有价值：只能挡 Pragon 类（BombPragon = 1 层炸弹 0DD 出 Pragon）
            has_pragon = (Move.Pragon in _opp_legal()) or (Move.BombPragon in _opp_legal())
            if not has_pragon:
                banned_idxs.append(i)
            continue
        if m == Move.ThreeDef:
            # 独有价值：只能挡 Three 类（FreeThree = 3 雷电 0DD 出 Three）
            has_three = ((Move.Three in _opp_legal()) or (Move.FreeThree in _opp_legal())
                         or (Move.FreeRotateThree in _opp_legal()) or (Move.RotateThree in _opp_legal()))
            if not has_three:
                banned_idxs.append(i)
            continue
        if m == Move.NieXiangDef:
            # 独有价值：只能挡 NieXiang（nxCharge>=4 时才出得来）
            has_niexiang = (Move.NieXiang in _opp_legal()) and (rl_opp.nxCharge >= 4)
            if not has_niexiang:
                banned_idxs.append(i)
            continue
        if m == Move.Def:
            # 价值：挡 Xiao(2 单位) 或 Bi(6 单位)。dd<2 单位时全没有 → 纯送才 ban
            if _opp_dd < 2:
                banned_idxs.append(i)
            continue
        if m == Move.Reflect:
            # 价值：反弹对手可反弹攻击(is_attack_move 且 非 is_unreflectable Shell/XiaoBei) 直接赢
            # 若对手合法动作里一个这样的攻击都没有 → 花 6 单位纯送，ban
            has_reflectable_atk = any(
                is_attack_move(om) and (not is_unreflectable(om)) for om in _opp_legal()
            )
            if not has_reflectable_atk:
                banned_idxs.append(i)
            continue
        # JuYan 不做额外 ban（它有下回合穿防 Xiao 的进攻收益，即使本回合没的防也经常有意义）
    if not banned_idxs:
        return moves, probs
    new_moves = []
    new_probs = []
    for i, m in enumerate(moves):
        if i in banned_idxs:
            continue
        new_moves.append(m)
        new_probs.append(probs[i])
    s = sum(new_probs)
    if s <= 1e-12 or not new_moves:
        return moves, probs
    new_probs = [p / s for p in new_probs]
    # ====== Reflect 硬概率上限：连续攒节奏（对手 lastMove=Charge 且 DD<=3）时，
    # 对手大概率继续攒/出小招，Reflect 触发率极低，出多了纯被剥削
    if rl_opp.lastMove == Move.Charge and rl_opp.dd <= 3 * kDDOne:
        opp_ddu = rl_opp.dd // kDDOne
        if opp_ddu <= 1:
            max_reflect = 0.12   # T2（1DD vs 1DD）: ≤12%
        elif opp_ddu == 2:
            max_reflect = 0.10   # T3（2DD vs 2DD）: ≤10%
        else:
            max_reflect = 0.10   # T4（3DD vs 3DD）: ≤10%
        if Move.Reflect in new_moves:
            ridx = new_moves.index(Move.Reflect)
            cur_reflect = new_probs[ridx]
            if cur_reflect > max_reflect:
                excess = cur_reflect - max_reflect
                new_probs[ridx] = max_reflect
                # 溢出概率优先转移给 Charge / Bi / LiQiang / Pragon（主动招）
                pref_targets = [m for m in (Move.Charge, Move.Bi, Move.LiQiang, Move.Pragon) if m in new_moves]
                if not pref_targets:
                    pref_targets = [m for m in new_moves if m not in {Move.Def, Move.JuYan, Move.Cloud}]
                pref_total = sum(new_probs[new_moves.index(m)] for m in pref_targets)
                if pref_total > 1e-12:
                    add_per = excess / pref_total
                    for m in pref_targets:
                        j = new_moves.index(m)
                        new_probs[j] += new_probs[j] * add_per
                else:
                    others_t = sum(new_probs[j] for j in range(len(new_moves)) if j != ridx)
                    if others_t > 1e-12:
                        scale = (others_t + excess) / others_t
                        for j in range(len(new_moves)):
                            if j == ridx: continue
                            new_probs[j] *= scale
                total_r = sum(new_probs)
                if total_r > 0:
                    new_probs = [p / total_r for p in new_probs]
    # ====== 落后 ≥2DD（对手 dd - 自己 dd >= 2DD=12 单位）的防守方专属保底规则：
    # 对手能出 Pragon/Three/Volvo/BigBi 等高威力攻击：Def 一个都挡不住（Def 只挡 Xiao/Bi）
    # 所以：
    #   1. TianLiJun（唯一挡 BigBi 的通用防御）保底 ≥12%
    #   2. 4 个专属防御按「对手能出对应攻击」的集合做保底：总合 ≥ 25%（且每单独的至少 6%）
    #   3. Def 硬上限 ≤30%（别把防御概率全浪费在只挡 Xiao/Bi 上）
    dd_behind = rl_opp.dd - rl_self.dd
    if dd_behind >= 2 * kDDOne:
        _opp_legal_set = set(list_legal_moves(rl_opp, rl_self))
        opp_has_pragon = (Move.Pragon in _opp_legal_set) or (Move.BombPragon in _opp_legal_set)
        opp_has_volvo = ((Move.Volvo in _opp_legal_set) or (Move.BombVolvo in _opp_legal_set)
                         or (Move.BombFlipVolvo in _opp_legal_set) or (Move.FlipVolvo in _opp_legal_set))
        opp_has_three = ((Move.Three in _opp_legal_set) or (Move.FreeThree in _opp_legal_set)
                         or (Move.FreeRotateThree in _opp_legal_set) or (Move.RotateThree in _opp_legal_set))
        opp_has_niexiang = (Move.NieXiang in _opp_legal_set) and (rl_opp.nxCharge >= 4)
        # (1) Def 硬上限 ≤30%
        if Move.Def in new_moves:
            didx = new_moves.index(Move.Def)
            max_def = 0.30
            if new_probs[didx] > max_def:
                excess_d = new_probs[didx] - max_def
                new_probs[didx] = max_def
                # 溢出按比例转移给：TianLiJun + 对手有对应攻击的专属防御 + JuYan
                transfer_pool = []
                if Move.TianLiJun in new_moves and (not rl_self.tianUses): transfer_pool.append(Move.TianLiJun)
                if opp_has_volvo and Move.VolvoDef in new_moves: transfer_pool.append(Move.VolvoDef)
                if opp_has_pragon and Move.PragonDef in new_moves: transfer_pool.append(Move.PragonDef)
                if opp_has_three and Move.ThreeDef in new_moves: transfer_pool.append(Move.ThreeDef)
                if opp_has_niexiang and Move.NieXiangDef in new_moves: transfer_pool.append(Move.NieXiangDef)
                if Move.JuYan in new_moves: transfer_pool.append(Move.JuYan)
                if len(transfer_pool) == 0:
                    transfer_pool = [m for m in new_moves if new_moves.index(m) != didx]
                tp_total = sum(new_probs[new_moves.index(m)] for m in transfer_pool if m in new_moves)
                if tp_total <= 1e-12:
                    add_p = excess_d / len(transfer_pool)
                    for m in transfer_pool:
                        if m in new_moves:
                            j = new_moves.index(m)
                            new_probs[j] += add_p
                else:
                    add_per = excess_d / tp_total
                    for m in transfer_pool:
                        if m in new_moves:
                            j = new_moves.index(m)
                            new_probs[j] += new_probs[j] * add_per
                t_def_cap = sum(new_probs)
                if t_def_cap > 0:
                    new_probs = [p / t_def_cap for p in new_probs]
        # (2) TianLiJun 保底 ≥12%（唯一能挡 BigBi 的）
        if Move.TianLiJun in new_moves and (not rl_self.tianUses):
            tidx = new_moves.index(Move.TianLiJun)
            min_tian = 0.12
            if new_probs[tidx] < min_tian:
                need_t = min_tian - new_probs[tidx]
                new_probs[tidx] = min_tian
                # 从 Def / Cloud / Charge / Absorb / Reflect 里抽（不要抽专属防御 / TianLiJun 自己）
                drain_src = [j for j, mv in enumerate(new_moves)
                             if j != tidx and mv in {Move.Def, Move.Cloud, Move.Charge, Move.Absorb, Move.Reflect}]
                drain_t = sum(new_probs[j] for j in drain_src)
                if drain_t >= need_t:
                    scale_tian = (drain_t - need_t) / drain_t
                    for j in drain_src:
                        new_probs[j] *= scale_tian
                else:
                    # 再从 JuYan 等其它非专属防御非 TianLiJun 里补
                    others_t = [j for j, mv in enumerate(new_moves)
                               if j != tidx and mv not in {
                                   Move.VolvoDef, Move.PragonDef, Move.ThreeDef, Move.NieXiangDef}]
                    others_total_t = sum(new_probs[j] for j in others_t)
                    if others_total_t >= need_t:
                        scale2 = (others_total_t - need_t) / others_total_t
                        for j in others_t:
                            new_probs[j] *= scale2
                t_tian_patch = sum(new_probs)
                if t_tian_patch > 0:
                    new_probs = [p / t_tian_patch for p in new_probs]
        # (3) 4 专属防御按「对手有对应攻击」集合保底：每个最小 6%，总≥25%
        spec_targets = []
        if opp_has_volvo and Move.VolvoDef in new_moves: spec_targets.append(Move.VolvoDef)
        if opp_has_pragon and Move.PragonDef in new_moves: spec_targets.append(Move.PragonDef)
        if opp_has_three and Move.ThreeDef in new_moves: spec_targets.append(Move.ThreeDef)
        if opp_has_niexiang and Move.NieXiangDef in new_moves: spec_targets.append(Move.NieXiangDef)
        if spec_targets:
            cur_sum_spec = 0.0
            for mv in spec_targets:
                j_ = new_moves.index(mv)
                cur_sum_spec += new_probs[j_]
            min_spec = min(0.25, 0.06 * len(spec_targets))
            if cur_sum_spec < min_spec:
                need_spec = min_spec - cur_sum_spec
                # 均分给每个 spec_target
                add_each = need_spec / len(spec_targets)
                for mv in spec_targets:
                    j_ = new_moves.index(mv)
                    new_probs[j_] += add_each
                # 从 Def / Cloud / Charge / Absorb / Reflect / JuYan 抽（不要碰 TianLiJun 和 4 专属防御自己）
                drain_src2 = [j for j, mv in enumerate(new_moves)
                              if mv in {Move.Def, Move.Cloud, Move.Charge, Move.Absorb, Move.Reflect, Move.JuYan}]
                drain_t2 = sum(new_probs[j] for j in drain_src2)
                if drain_t2 >= need_spec:
                    sc_spec = (drain_t2 - need_spec) / drain_t2
                    for j in drain_src2:
                        new_probs[j] *= sc_spec
                else:
                    excluded = set(spec_targets) | {Move.TianLiJun}
                    others_s = [j for j, mv in enumerate(new_moves) if mv not in excluded]
                    ot2 = sum(new_probs[j] for j in others_s)
                    if ot2 >= need_spec:
                        scc = (ot2 - need_spec) / ot2
                        for j in others_s:
                            new_probs[j] *= scc
                t_spec_patch = sum(new_probs)
                if t_spec_patch > 0:
                    new_probs = [p / t_spec_patch for p in new_probs]
    # ====== 连续攒节奏下 Charge 最小保底概率（T2 / T3 时 Charge 不能 < 15%，否则相当于纯送攒节奏）
    if rl_opp.lastMove == Move.Charge and rl_self.dd <= 2 * kDDOne and Move.Charge in new_moves:
        min_charge = 0.15
        cidx = new_moves.index(Move.Charge)
        if new_probs[cidx] < min_charge:
            need = min_charge - new_probs[cidx]
            new_probs[cidx] = min_charge
            # 从 Reflect/Def/Absorb/JuYan/Cloud 防御类/反制类均匀抽走 excess
            drain_pool = [j for j, m in enumerate(new_moves) if j != cidx and m in {
                Move.Reflect, Move.Def, Move.JuYan, Move.Cloud, Move.Absorb,
                Move.PragonDef, Move.VolvoDef, Move.NieXiangDef, Move.ThreeDef}]
            drain_total = sum(new_probs[j] for j in drain_pool)
            if drain_total > need:
                scale = (drain_total - need) / drain_total
                for j in drain_pool:
                    new_probs[j] *= scale
            else:
                others = [j for j in range(len(new_moves)) if j != cidx]
                ot = sum(new_probs[j] for j in others)
                if ot > 1e-12:
                    need_scale = (ot - need) / ot
                    for j in others:
                        new_probs[j] *= need_scale
            t_charge_min = sum(new_probs)
            if t_charge_min > 0:
                new_probs = [p / t_charge_min for p in new_probs]
    boost_rules = []
    # 注意：连招 boost 是「RL 自己」的连招，所以取 rl_self
    if rl_self.bombLayers == 2 and Move.BombPragon in new_moves:
        boost_rules.append((Move.BombPragon, 0.35, "炸药2层"))
    if rl_self.lightning >= 3 and Move.FreeThree in new_moves:
        boost_rules.append((Move.FreeThree, 0.40, "雷电>=3层"))
    if rl_self.nxCharge >= 4 and rl_self.juyanBuff and Move.Xiao in new_moves:
        boost_rules.append((Move.Xiao, 0.30, "聂湘4充+距喦"))
    if boost_rules:
        for target, min_prob, label in boost_rules:
            if target not in new_moves:
                continue
            idx = new_moves.index(target)
            cur = new_probs[idx]
            if cur >= min_prob:
                continue
            excess = min_prob - cur
            new_probs[idx] = min_prob
            others_total = sum(new_probs[j] for j in range(len(new_moves)) if j != idx)
            if others_total <= 1e-12:
                continue
            scale = (others_total - excess) / others_total
            for j in range(len(new_moves)):
                if j == idx:
                    continue
                new_probs[j] = max(0.0, new_probs[j] * scale)
            t_boost = sum(new_probs)
            if t_boost > 0:
                new_probs = [p / t_boost for p in new_probs]
    return new_moves, new_probs


def rl_strategy_distribution_core(model, has_mask: bool,
                                  cpu_state: PlayerState,
                                  player_state: PlayerState,
                                  obs, mask, legal_moves) -> Tuple[List[Move], List[float]]:
    if model is None:
        return _fallback_distribution(legal_moves)
    probs_full = None
    try:
        import torch
        with torch.no_grad():
            obs_t = torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0).to(model.device)
            dist = model.policy.get_distribution(obs_t)
            try:
                raw = dist.distribution.probs
                if raw is not None and raw.numel() == NUM_MOVES:
                    probs_full = raw[0].cpu().numpy().tolist()
            except Exception:
                probs_full = None
            if probs_full is None:
                try:
                    logits = dist.distribution.logits
                    if logits is not None and logits.numel() == NUM_MOVES:
                        lg = logits[0].cpu().numpy()
                        lg = lg - lg.max()
                        probs_full = [0.0] * NUM_MOVES
                        total = 0.0
                        for i in range(NUM_MOVES):
                            if mask[i]:
                                v = float(lg[i])
                                v = math.exp(v) if (v == v) and v > -1e38 else 0.0
                                probs_full[i] = v
                                total += v
                        if total > 1e-12:
                            probs_full = [p / total for p in probs_full]
                except Exception:
                    probs_full = None
    except Exception:
        probs_full = None
    if probs_full is None:
        return _fallback_distribution(legal_moves)
    idxs = [MOVE_TO_IDX[m] for m in legal_moves]
    vals = [float(probs_full[i]) for i in idxs]
    s = sum(vals)
    if s <= 1e-12:
        return _fallback_distribution(legal_moves)
    vals = [v / s for v in vals]
    moves, probs = legal_moves, vals
    return _apply_expert_heuristic_filter(cpu_state, player_state, moves, probs)


def rl_strategy_distribution(cpu_state: PlayerState,
                             player_state: PlayerState,
                             checkpoint_path: Optional[str] = None,
                             device: str = "cpu") -> Tuple[list, list]:
    model, has_mask = _load_model(checkpoint_path, device=device)
    legal_moves = list_legal_moves(cpu_state, player_state)
    if model is None:
        if not legal_moves:
            return [], []
        return legal_moves, [1.0 / len(legal_moves)] * len(legal_moves)
    obs, mask = _obs_and_mask(cpu_state, player_state)
    return rl_strategy_distribution_core(model, has_mask, cpu_state, player_state, obs, mask, legal_moves)


def debug_dump_strategy(cpu_state: PlayerState, player_state: PlayerState,
                        label: str = "", top_k: int = 15,
                        checkpoint_path: Optional[str] = None) -> str:
    lines = []
    if label:
        lines.append(f"--- {label} ---")
    moves, probs = rl_strategy_distribution(cpu_state, player_state, checkpoint_path)
    if not moves:
        return "\n".join(lines + ["(no legal moves)"])
    pairs = sorted(zip(moves, probs), key=lambda x: -x[1])
    entropy = 0.0
    for _, p in pairs:
        if p > 0:
            entropy -= p * math.log(p, 2)
    lines.append(f"合法={len(moves)}  熵={entropy:.3f} bits  (最大熵≈{math.log(len(moves), 2):.2f})")
    cum = 0.0
    for rank, (m, pr) in enumerate(pairs[:top_k], 1):
        cum += pr
        name = MOVE_NAMES_CN.get(m, m.name)
        bar = "#" * max(1, int(round(pr * 50)))
        lines.append(f"  {rank:>2d}. {name:<22s} {pr:>7.2%}  cum={cum:>7.2%}  {bar}")
    if len(pairs) > top_k:
        lines.append(f"  ... 其余 {len(pairs) - top_k} 个 合概率={1 - cum:.2%}")
    return "\n".join(lines)
