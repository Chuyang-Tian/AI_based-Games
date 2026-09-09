from __future__ import annotations
from typing import Tuple, Dict, Any, Optional, List, Callable
import gymnasium as gym
from gymnasium import spaces

from deidei_env import (
    PlayerState, Move, Outcome, ALL_MOVES,
    list_legal_moves, simulate_turn, kDDOne,
)

NUM_MOVES = len(ALL_MOVES)
MOVE_TO_IDX = {m: i for i, m in enumerate(ALL_MOVES)}

DD_CAP = 20 * kDDOne
LIGHTNING_CAP = 12
USES_CAP = 10
BOMB_LAYERS_CAP = 10
BOMB_PENDING_CAP = 5
NXCHARGE_CAP = 10

NUM_MOVE_SLOTS = NUM_MOVES + 1
NOMOVE_IDX = NUM_MOVES

CHARGE_IDX = MOVE_TO_IDX[Move.Charge]


def _move_to_idx(m: Move) -> int:
    if m == Move.NoMove:
        return NOMOVE_IDX
    return MOVE_TO_IDX.get(m, NOMOVE_IDX)


import math as _math


def _clip01f(x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return x


def _encode_player_state_list(s: PlayerState) -> list:
    out = [0.0] * (14 + NUM_MOVE_SLOTS * 2)
    p = 0
    out[p] = _clip01f(s.dd / DD_CAP); p += 1
    out[p] = _clip01f(s.lightning / LIGHTNING_CAP); p += 1
    out[p] = _clip01f(s.cloudUses / USES_CAP); p += 1
    out[p] = _clip01f(s.bombUses / USES_CAP); p += 1
    out[p] = _clip01f(s.bombLayers / BOMB_LAYERS_CAP); p += 1
    bp = s.bombPending
    out[p] = _clip01f(bp[0] / BOMB_PENDING_CAP); p += 1
    out[p] = _clip01f(bp[1] / BOMB_PENDING_CAP); p += 1
    out[p] = _clip01f(bp[2] / BOMB_PENDING_CAP); p += 1
    out[p] = _clip01f(s.tianUses / USES_CAP); p += 1
    out[p] = (1.0 if s.juyanBuff else 0.0); p += 1
    out[p] = _clip01f(s.nxCharge / NXCHARGE_CAP); p += 1
    out[p] = (1.0 if s.zhangUsed else 0.0); p += 1
    out[p] = (1.0 if s.liqUsed else 0.0); p += 1
    out[p] = (1.0 if s.hasHighAttackRecord else 0.0); p += 1
    ha = _move_to_idx(s.lastHighAttack)
    out[p + ha] = 1.0
    p += NUM_MOVE_SLOTS
    lm = _move_to_idx(s.lastMove)
    out[p + lm] = 1.0
    return out


import numpy as np

_EMPTY_MASK_BUF = np.zeros(NUM_MOVES, dtype=np.int8)


def _legal_mask_fast(self_s: PlayerState, opp_s: PlayerState, out=None) -> np.ndarray:
    if out is None:
        out = np.zeros(NUM_MOVES, dtype=np.int8)
    else:
        out.fill(0)
    for m in list_legal_moves(self_s, opp_s):
        out[MOVE_TO_IDX[m]] = 1
    if out[0] == 0 and out.sum() == 0:
        out[CHARGE_IDX] = 1
    return out


_OBS_BUF_A = [0.0]
_OBS_BUF_B = [0.0]


def _concat_obs_list(self_s: PlayerState, opp_s: PlayerState):
    a = _encode_player_state_list(self_s)
    b = _encode_player_state_list(opp_s)
    return a, b


_per_player_len = len(_encode_player_state_list(PlayerState()))
OBS_DIM = _per_player_len * 2
_OBS_NP_BUF = np.zeros(OBS_DIM, dtype=np.float32)


def _concat_obs(self_s: PlayerState, opp_s: PlayerState, out=None) -> np.ndarray:
    a, b = _concat_obs_list(self_s, opp_s)
    if out is None:
        out = np.empty(OBS_DIM, dtype=np.float32)
    out[:_per_player_len] = a
    out[_per_player_len:] = b
    return out


_mask_buf = np.zeros(NUM_MOVES, dtype=np.int8)
_obs_buf_step = np.zeros(OBS_DIM, dtype=np.float32)
_obs_buf_reset = np.zeros(OBS_DIM, dtype=np.float32)


def _legal_mask(self_s: PlayerState, opp_s: PlayerState) -> np.ndarray:
    return _legal_mask_fast(self_s, opp_s)


_OPPONENT_FN = Callable[[PlayerState, PlayerState, Optional[Any]], Move]


class DeiDeiSelfPlayEnv(gym.Env):
    metadata = {"render_modes": ["ansi"]}

    def __init__(self, opponent_fn: Optional[_OPPONENT_FN] = None,
                 opponent_payload: Optional[Any] = None,
                 max_turns: int = 120,
                 reward_shaping: bool = True,
                 use_buffers: bool = True):
        super().__init__()
        self.action_space = spaces.Discrete(NUM_MOVES)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(OBS_DIM,), dtype=np.float32)
        self.opponent_fn = opponent_fn
        self.opponent_payload = opponent_payload
        self.max_turns = max_turns
        self.reward_shaping = reward_shaping
        self.use_buffers = use_buffers
        self.turn = 0
        self.self_state = PlayerState()
        self.opp_state = PlayerState()
        self._obs_buf = np.zeros(OBS_DIM, dtype=np.float32) if use_buffers else None
        self._mask_buf = np.zeros(NUM_MOVES, dtype=np.int8) if use_buffers else None

    def _default_opponent(self, opp_s: PlayerState, self_s: PlayerState, payload) -> Move:
        from deidei_env import choose_easy_move
        rng = random_default()
        return choose_easy_move(opp_s, self_s, rng)

    def _get_opp_move(self) -> Move:
        if self.opponent_fn is None:
            return self._default_opponent(self.opp_state, self.self_state, self.opponent_payload)
        try:
            return self.opponent_fn(self.opp_state, self.self_state, self.opponent_payload)
        except TypeError:
            return self.opponent_fn(self.opp_state, self.self_state)

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.turn = 0
        self.self_state = PlayerState()
        self.opp_state = PlayerState()
        self.opp_state_prev_lastMove = self.opp_state.lastMove
        if options:
            if "self_state" in options:
                self.self_state = PlayerState(**options["self_state"].__dict__)
            if "opp_state" in options:
                self.opp_state = PlayerState(**options["opp_state"].__dict__)
                self.opp_state_prev_lastMove = self.opp_state.lastMove
            if "opponent_fn" in options:
                self.opponent_fn = options["opponent_fn"]
            if "opponent_payload" in options:
                self.opponent_payload = options["opponent_payload"]
        ob = _concat_obs(self.self_state, self.opp_state,
                         out=(self._obs_buf if self.use_buffers else None))
        mk = _legal_mask_fast(self.self_state, self.opp_state,
                              out=(self._mask_buf if self.use_buffers else None))
        info = {"action_mask": mk.copy() if self.use_buffers else mk}
        return ob, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        if 0 <= action < NUM_MOVES:
            self_move = ALL_MOVES[action]
        else:
            self_move = Move.Charge
        opp_move = self._get_opp_move()

        prev_self_dd = self.self_state.dd
        prev_opp_dd = self.opp_state.dd
        prev_self_bomb = self.self_state.bombLayers
        prev_self_lightning = self.self_state.lightning
        prev_self_nx = self.self_state.nxCharge
        prev_opp_nx = self.opp_state.nxCharge
        prev_self_juyan = self.self_state.juyanBuff
        tr = simulate_turn(self.self_state, self.opp_state, self_move, opp_move)
        self.self_state = tr.nextP
        self.opp_state = tr.nextC
        self.turn += 1

        if tr.outcome == Outcome.PlayerWin:
            reward = 1.0
        elif tr.outcome == Outcome.CpuWin:
            reward = -1.0
        else:
            reward = 0.0
            if tr.outcome == Outcome.Continue and self.reward_shaping:
                dd_diff = (self.self_state.dd - self.opp_state.dd) * (1.0 / (kDDOne * 10.0))
                prev_diff = (prev_self_dd - prev_opp_dd) * (1.0 / (kDDOne * 10.0))
                reward = 0.02 * (dd_diff - prev_diff)
                if self_move == Move.LiQiang:
                    opp_prev_last = self.opp_state_prev_lastMove
                    if opp_prev_last == Move.NoMove:
                        reward -= 0.03
                    else:
                        opp_now_legal = list_legal_moves(self.opp_state, self.self_state)
                        if opp_prev_last not in opp_now_legal:
                            reward -= 0.03
                is_first_turn = (self.turn == 1
                                 and prev_self_dd == 0
                                 and prev_opp_dd == 0)
                PURELY_DEFENSIVE_NO_DD_NEEDED = {Move.Def, Move.PragonDef, Move.VolvoDef,
                                                 Move.NieXiangDef, Move.ThreeDef, Move.JuYan}
                if is_first_turn and self_move in PURELY_DEFENSIVE_NO_DD_NEEDED:
                    reward -= 0.02
                if is_first_turn and self_move == Move.TianLiJun:
                    reward -= 0.04
                if is_first_turn and self_move == Move.Cloud:
                    reward -= 0.04
                if is_first_turn and self_move == Move.LiQiang:
                    reward -= 0.03
                if self_move == Move.NieXiangDef and self.opp_state.nxCharge < 4:
                    reward -= 0.03
                # （上面三条 NX<4 / lightning<1 / bombLayers<1 的惩罚已经保留，和下面的口径一致，冗余但保险）
                dd_diff = prev_self_dd - prev_opp_dd
                if dd_diff >= kDDOne * 5 and self_move in PURELY_DEFENSIVE_NO_DD_NEEDED:
                    reward -= 0.03
                if dd_diff <= -kDDOne * 5 and self_move == Move.Suicide:
                    reward -= 0.50
                # 连续攒节奏下（对手上回合=Charge 且对手 DD<=3）Reflect 触发率极低，轻惩罚
                if self_move == Move.Reflect and self.opp_state_prev_lastMove == Move.Charge:
                    if prev_opp_dd <= 3 * kDDOne:
                        reward -= 0.02
                # === 防御类「真·无独有价值 → 纯送回合」重罚（跟推理侧 _apply_expert_heuristic_filter 口径完全一致）
                # blocks_attack 核心推论：
                #   Bi 只有 Def/TianLiJun/Bomb/JuYan 能挡！4 专属防御全挡不住 Bi →
                #   4 专属防御有独有价值 ↔ 对手能出对应专属攻击（Def 挡不住的那种）
                #   否则，Def 严格占优（既挡 Xiao 又挡 Bi）→ 4 专属防御直接罚到没
                opp_legal_quick = list_legal_moves(self.opp_state, self.self_state)
                opp_lgl_set = set(opp_legal_quick)
                opp_has_pragon = (Move.Pragon in opp_lgl_set) or (Move.BombPragon in opp_lgl_set)
                opp_has_volvo = ((Move.Volvo in opp_lgl_set) or (Move.BombVolvo in opp_lgl_set)
                                 or (Move.BombFlipVolvo in opp_lgl_set) or (Move.FlipVolvo in opp_lgl_set))
                opp_has_three = ((Move.Three in opp_lgl_set) or (Move.FreeThree in opp_lgl_set)
                                 or (Move.FreeRotateThree in opp_lgl_set) or (Move.RotateThree in opp_lgl_set))
                opp_has_niexiang = (Move.NieXiang in opp_lgl_set) and (prev_opp_nx >= 4)
                if self_move == Move.VolvoDef and not opp_has_volvo:
                    reward -= 0.03
                if self_move == Move.PragonDef and not opp_has_pragon:
                    reward -= 0.03
                if self_move == Move.ThreeDef and not opp_has_three:
                    reward -= 0.03
                if self_move == Move.NieXiangDef and not opp_has_niexiang:
                    reward -= 0.03
                if self_move == Move.Def and prev_opp_dd < 2:
                    reward -= 0.02
                # === 落后≥2DD（对手-自己≥12单位）防守方口径同步（跟推理侧 BUG3 规则完全对齐）
                # 对手可以出 Pragon/Three/Volvo/BigBi 等高威力 →
                #   正奖励：TianLiJun（唯一挡 BigBi）+ 对手有对应攻击的 4 专属防御 + JuYan
                #   负奖励：Def 占比太高（只挡 Xiao/Bi）给 -0.01 引导概率转移
                behind_2dd = (prev_opp_dd - prev_self_dd) >= 2 * kDDOne
                if behind_2dd:
                    # Def 占比过高时软惩罚（上限 30%，但在 reward 里只是轻引导，避免硬 cap 的替代方案）
                    if self_move == Move.Def and (prev_opp_dd - prev_self_dd) >= 4 * kDDOne:
                        reward -= 0.01   # 大落后（4DD以上）Def 占比太高轻罚
                    if self_move == Move.TianLiJun and (not self.self_state.tianUses):
                        reward += 0.02   # TianLiJun 唯一挡 BigBi，鼓励
                    # 4 专属防御：对手有对应攻击时才鼓励
                    if self_move == Move.VolvoDef and opp_has_volvo:
                        reward += 0.015
                    if self_move == Move.PragonDef and opp_has_pragon:
                        reward += 0.015
                    if self_move == Move.ThreeDef and opp_has_three:
                        reward += 0.015
                    if self_move == Move.NieXiangDef and opp_has_niexiang:
                        reward += 0.015
                # JuYan 不罚（它有下回合穿防免费 Xiao 的进攻收益，本回合没的防也经常对）
                # === 连招 reward 跟推理侧 boost 口径对齐
                # BUG1 同步：炸药延迟从 C→B，bombLayers==1 就可以出 BombPragon（之前只有 bombLayers==2 才 +0.05，太窄）
                if self_move == Move.BombPragon and prev_self_bomb >= 1:
                    reward += 0.04
                if self_move == Move.BombVolvo and prev_self_bomb >= 2:
                    reward += 0.04
                if self_move == Move.FreeThree and prev_self_lightning >= 3:
                    reward += 0.05
                if self_move == Move.FreeRotateThree and prev_self_lightning >= 6:
                    reward += 0.04
                if self_move == Move.Xiao and prev_self_nx >= 4 and prev_self_juyan:
                    reward += 0.04
                if self_move == Move.NieXiang and prev_self_nx >= 4 and prev_self_juyan:
                    reward += 0.02
                # === BUG2 同步：Zhang(复制A) + A 连出 也属于 LiQiang 触发链（之前只在 opp_prev_last==A 时认定 LiQiang 机会）
                if self_move == Move.LiQiang:
                    opp_prev_last = self.opp_state_prev_lastMove
                    if opp_prev_last == Move.ZhangXinWei:
                        # 对手上回合是 ZhangXinWei（复制了上上次的 highAttack=opp_state.lastHighAttack）
                        # 这回合如果对手出"等效于"这个复制招，也会触发 LiQiang，所以 LiQiang 也是正收益机会
                        # 不罚（但 NoMove 那种还是会罚的上面已经覆盖）
                        pass

        terminated = tr.outcome != Outcome.Continue
        truncated = (not terminated) and (self.turn >= self.max_turns)
        if truncated:
            extra = (self.self_state.dd - self.opp_state.dd) * (1.0 / (kDDOne * 20.0))
            reward += extra
            if reward < -1.0:
                reward = -1.0
            elif reward > 1.0:
                reward = 1.0

        ob = _concat_obs(self.self_state, self.opp_state,
                         out=(self._obs_buf if self.use_buffers else None))
        mk = _legal_mask_fast(self.self_state, self.opp_state,
                              out=(self._mask_buf if self.use_buffers else None))
        info = {
            "action_mask": mk.copy() if self.use_buffers else mk,
            "outcome": tr.outcome,
            "turn": self.turn,
            "self_move": self_move,
            "opp_move": opp_move,
        }
        self.opp_state_prev_lastMove = self.opp_state.lastMove
        return ob, reward, terminated, truncated, info

    def render(self) -> Optional[str]:
        from deidei_env import _evaluate_state_heuristic
        v = _evaluate_state_heuristic(self.self_state, self.opp_state)
        return ("T%d  self_dd=%d  opp_dd=%d  value≈%.3f"
                % (self.turn, self.self_state.dd // 6, self.opp_state.dd // 6, v))


import random as _random_mod

_RNG_INSTANCE = _random_mod.Random(0xC0FFEE)


def random_default() -> _random_mod.Random:
    return _RNG_INSTANCE
