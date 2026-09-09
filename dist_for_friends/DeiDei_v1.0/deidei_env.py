from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple, Dict, Optional
import random
import math

kDDDen = 6
kDDOne = 6

class Outcome(Enum):
    Continue = 0
    PlayerWin = 1
    CpuWin = 2
    Draw = 3

class Move(Enum):
    NoMove = auto()
    Charge = auto()
    Bi = auto()
    Def = auto()
    Three = auto()
    ThreeDef = auto()
    BigBi = auto()
    Reflect = auto()
    Suicide = auto()
    Cloud = auto()
    Bomb = auto()
    Xiao = auto()
    Pragon = auto()
    PragonDef = auto()
    Volvo = auto()
    VolvoDef = auto()
    RotateThree = auto()
    XiaoBei = auto()
    FlipVolvo = auto()
    Shell = auto()
    Absorb = auto()
    NieXiang = auto()
    NieXiangDef = auto()
    JuYan = auto()
    TianLiJun = auto()
    ZhangXinWei = auto()
    LiQiang = auto()
    BombPragon = auto()
    BombVolvo = auto()
    BombFlipVolvo = auto()
    FreeThree = auto()
    FreeRotateThree = auto()

@dataclass
class PlayerState:
    dd: int = 0
    lightning: int = 0
    cloudUses: int = 0
    bombUses: int = 0
    bombLayers: int = 0
    bombPending: List[int] = field(default_factory=lambda: [0,0,0])
    tianUses: int = 0
    juyanBuff: bool = False
    nxCharge: int = 0
    zhangUsed: bool = False
    liqUsed: bool = False
    hasHighAttackRecord: bool = False
    lastHighAttack: Move = Move.Charge
    lastMove: Move = Move.NoMove

def clamp_nonneg(x: int) -> int:
    return x if x >= 0 else 0

def is_attack_move(m: Move) -> bool:
    return m in {
        Move.Xiao, Move.Bi, Move.Pragon, Move.Three, Move.NieXiang,
        Move.Volvo, Move.BigBi, Move.RotateThree, Move.XiaoBei,
        Move.FlipVolvo, Move.Shell, Move.BombPragon, Move.BombVolvo,
        Move.BombFlipVolvo, Move.FreeThree, Move.FreeRotateThree
    }

def is_quantum_move(m: Move) -> bool:
    return m in {Move.RotateThree, Move.FlipVolvo, Move.FreeRotateThree}

def is_counter_move(m: Move) -> bool:
    return m in {Move.Reflect, Move.Absorb, Move.Cloud, Move.Suicide}

def is_high_attack_for_zhang(m: Move) -> bool:
    return m in {
        Move.Pragon, Move.Three, Move.Volvo, Move.BigBi, Move.Shell,
        Move.XiaoBei, Move.RotateThree, Move.FlipVolvo, Move.NieXiang,
        Move.BombPragon, Move.BombVolvo, Move.BombFlipVolvo,
        Move.FreeThree, Move.FreeRotateThree
    }

def attack_power_units(m: Move, xiao_enhanced: bool) -> int:
    if m == Move.Xiao: return 2
    if m == Move.Bi: return 6
    if m == Move.Pragon: return 12
    if m == Move.Three: return 18
    if m == Move.NieXiang: return 21
    if m == Move.Volvo: return 24
    if m == Move.BigBi: return 30
    if m == Move.RotateThree: return 36
    if m == Move.XiaoBei: return 42
    if m == Move.FlipVolvo: return 48
    if m == Move.Shell: return 60
    if m == Move.BombPragon: return 12
    if m == Move.BombVolvo: return 24
    if m == Move.BombFlipVolvo: return 48
    if m == Move.FreeThree: return 18
    if m == Move.FreeRotateThree: return 36
    if xiao_enhanced and m == Move.Xiao: return 2
    return 0

def is_shell_like(m: Move) -> bool:
    return m in {Move.Shell, Move.XiaoBei}

def is_unreflectable(m: Move) -> bool:
    return m in {Move.Shell, Move.XiaoBei}

def is_unabsorbable(m: Move) -> bool:
    if m in {Move.Shell, Move.XiaoBei, Move.NieXiang}:
        return True
    if m in {Move.RotateThree, Move.FlipVolvo, Move.FreeRotateThree}:
        return True
    return False

def is_absorbable_attack(m: Move, xiao_enhanced: bool) -> bool:
    if not is_attack_move(m): return False
    if is_unabsorbable(m): return False
    if m in {Move.Volvo, Move.BombVolvo, Move.BombFlipVolvo, Move.FlipVolvo, Move.RotateThree}:
        return False
    if xiao_enhanced and m == Move.Xiao: return True
    if m in {Move.Xiao, Move.Bi, Move.Pragon, Move.Three, Move.BigBi, Move.BombPragon, Move.FreeThree}:
        return True
    return False

def is_blocked_by_any_defense(m: Move, xiao_enhanced: bool) -> bool:
    if xiao_enhanced and m == Move.Xiao: return False
    return m == Move.Xiao

def dd_cost_units_for_move(self: PlayerState, m: Move) -> int:
    if m == Move.Charge: return 0
    if m == Move.Bi: return 6
    if m == Move.Def: return 0
    if m == Move.Three: return 18
    if m == Move.ThreeDef: return 0
    if m == Move.BigBi: return 30
    if m == Move.Reflect: return 6
    if m == Move.Suicide: return 0
    if m == Move.Cloud: return 0 if self.cloudUses == 0 else 6
    if m == Move.Bomb: return 6
    if m == Move.Xiao: return 2
    if m == Move.Pragon: return 12
    if m == Move.PragonDef: return 0
    if m == Move.Volvo: return 24
    if m == Move.VolvoDef: return 0
    if m == Move.RotateThree: return 36
    if m == Move.XiaoBei: return 42
    if m == Move.FlipVolvo: return 48
    if m == Move.Shell: return 60
    if m == Move.Absorb: return 6
    if m == Move.NieXiang: return 0
    if m == Move.NieXiangDef: return 0
    if m == Move.JuYan: return 0
    if m == Move.TianLiJun: return 0 if self.tianUses == 0 else 3
    if m == Move.ZhangXinWei: return 0
    if m == Move.LiQiang: return 0
    if m == Move.BombPragon: return 0
    if m == Move.BombVolvo: return 0
    if m == Move.BombFlipVolvo: return 0
    if m == Move.FreeThree: return 0
    if m == Move.FreeRotateThree: return 0
    return 0

ALL_MOVES = [
    Move.Charge, Move.Bi, Move.Def, Move.Three, Move.ThreeDef, Move.BigBi, Move.Reflect, Move.Suicide,
    Move.Cloud, Move.Bomb, Move.Xiao, Move.Pragon, Move.PragonDef, Move.Volvo, Move.VolvoDef,
    Move.RotateThree, Move.XiaoBei, Move.FlipVolvo, Move.Shell, Move.Absorb, Move.NieXiang,
    Move.NieXiangDef, Move.JuYan, Move.TianLiJun, Move.ZhangXinWei, Move.LiQiang,
    Move.BombPragon, Move.BombVolvo, Move.BombFlipVolvo, Move.FreeThree, Move.FreeRotateThree
]

def is_legal_move(self: PlayerState, opp: PlayerState, m: Move) -> bool:
    if m == Move.ZhangXinWei:
        return (not self.zhangUsed) and self.hasHighAttackRecord
    if m == Move.LiQiang:
        return not self.liqUsed
    if m == Move.NieXiang:
        return self.nxCharge >= 4
    if m == Move.BombPragon:
        return self.bombLayers >= 1
    if m == Move.BombVolvo:
        return self.bombLayers >= 2
    if m == Move.BombFlipVolvo:
        return self.bombLayers >= 4
    if m == Move.FreeThree:
        return self.lightning >= 3
    if m == Move.FreeRotateThree:
        return self.lightning >= 6
    cost = dd_cost_units_for_move(self, m)
    if self.dd < cost: return False
    # defense moves allowed regardless
    return True

def list_legal_moves(self: PlayerState, opp: PlayerState) -> List[Move]:
    return [m for m in ALL_MOVES if is_legal_move(self, opp, m)]

@dataclass
class Action:
    declared: Move
    effective: Move
    xiaoEnhanced: bool = False
    ddCost: int = 0
    bombLayerCost: int = 0
    lightningCost: int = 0
    nxCost: int = 0
    triggersLiQiangWin: bool = False
    liQiangAsCharge: bool = False

def build_action(self: PlayerState, opp: PlayerState, declared: Move) -> Action:
    a = Action(declared=declared, effective=declared)
    if declared == Move.LiQiang:
        # 在不知道对手本回合招式之前，默认按“不触发 → 视为攒”占位
        # 双方招式都确定后，再在 compute_liqiang_triggers(...) 里重新判定
        a.triggersLiQiangWin = False
        a.liQiangAsCharge = True
        a.effective = Move.Charge
    if declared == Move.ZhangXinWei:
        a.effective = self.lastHighAttack
    elif declared == Move.BombPragon:
        a.effective = Move.Pragon
    elif declared == Move.BombVolvo:
        a.effective = Move.Volvo
    elif declared == Move.BombFlipVolvo:
        a.effective = Move.FlipVolvo
    elif declared == Move.FreeThree:
        a.effective = Move.Three
    elif declared == Move.FreeRotateThree:
        a.effective = Move.RotateThree
    a.ddCost = dd_cost_units_for_move(self, declared)
    if declared == Move.Xiao and self.juyanBuff:
        a.xiaoEnhanced = True
        a.ddCost = 0
    if declared == Move.BombPragon: a.bombLayerCost = 1
    if declared == Move.BombVolvo: a.bombLayerCost = 2
    if declared == Move.BombFlipVolvo: a.bombLayerCost = 4
    if declared == Move.FreeThree: a.lightningCost = 3
    if declared == Move.FreeRotateThree: a.lightningCost = 6
    if declared == Move.NieXiang: a.nxCost = 4
    return a


def compute_liqiang_triggers(p0: PlayerState, c0: PlayerState, pAct: Action, cAct: Action):
    """
    历强规则：我出历强时，当且仅当「对手本回合出的招式（考虑 Zhang 复制的有效动作！）
    == 对手上一回合最后出的招式（也考虑上回合是 Zhang 的有效动作）」，我直接赢；否则按攒结算。
    ——正确：上回合出 Zhang(复制Bi) → effective=Bi；这回合对手出 Bi → 等于上回合 effective=Bi → 触发历强
    另外：如果对手上回合就是 ZhangXinWei（复制了某攻击），我们也应当用「上回合 effective」（而不是 declared ZhangXinWei）
    才能正确识别连续攻击链（ZhangBi+Bi 也算连）。
    """
    def _last_move_effective(p: PlayerState, a_prev_declared: Move) -> Move:
        # 如果上回合就是 ZhangXinWei，它的 effective 是 p.lastHighAttack（因为 build_action 就是 effective=self.lastHighAttack）
        # 如果上回合不是 Zhang，effective 就是 declared
        if a_prev_declared == Move.ZhangXinWei:
            return p.lastHighAttack
        return a_prev_declared

    if pAct.declared == Move.LiQiang:
        # 对手上回合 lastMove(declared) → effective 化
        c_prev_eff = _last_move_effective(c0, c0.lastMove)
        # 对手本回合 declared → effective 化（用已经在 build_action 里填好的 cAct.effective，Zhang 已经正确映射）
        c_curr_eff = cAct.effective
        trigger = (c_curr_eff == c_prev_eff)
        pAct.triggersLiQiangWin = bool(trigger)
        pAct.liQiangAsCharge = (not trigger)
        if trigger:
            pAct.effective = Move.LiQiang
        else:
            pAct.effective = Move.Charge
    if cAct.declared == Move.LiQiang:
        p_prev_eff = _last_move_effective(p0, p0.lastMove)
        p_curr_eff = pAct.effective
        trigger = (p_curr_eff == p_prev_eff)
        cAct.triggersLiQiangWin = bool(trigger)
        cAct.liQiangAsCharge = (not trigger)
        if trigger:
            cAct.effective = Move.LiQiang
        else:
            cAct.effective = Move.Charge

def interpretations(a: Action) -> List[Move]:
    if a.effective == Move.RotateThree: return [Move.Three, Move.Suicide]
    if a.effective == Move.FlipVolvo: return [Move.Volvo, Move.Suicide]
    return [a.effective]

# resolveNoQuantum: core pairing logic

def blocks_attack(defender: PlayerState, defAct: Action, defMove: Move, atkMove: Move, atkXiaoEnhanced: bool) -> bool:
    if not is_attack_move(atkMove): return False
    if atkMove in {Move.Shell, Move.XiaoBei}: return False
    if atkMove == Move.BigBi:
        if defMove == Move.TianLiJun: return True
        return False
    if atkMove == Move.Three:
        if defMove == Move.ThreeDef: return True
        if defMove == Move.TianLiJun: return True
        if defMove == Move.Bomb:
            x = defender.bombUses + 1
            if x > 4: x = 4
            threshold = (x - 1) * kDDOne
            return attack_power_units(atkMove, atkXiaoEnhanced) <= threshold
        if is_blocked_by_any_defense(atkMove, atkXiaoEnhanced): return defMove == Move.JuYan
        return False
    if atkMove == Move.Volvo:
        if defMove == Move.VolvoDef: return True
        if defMove == Move.TianLiJun: return True
        return False
    if atkMove == Move.Pragon:
        if defMove == Move.PragonDef: return True
        if defMove == Move.TianLiJun: return True
        if defMove == Move.Bomb:
            x = defender.bombUses + 1
            if x > 4: x = 4
            threshold = (x - 1) * kDDOne
            return attack_power_units(atkMove, atkXiaoEnhanced) <= threshold
        if is_blocked_by_any_defense(atkMove, atkXiaoEnhanced): return defMove == Move.JuYan
        return False
    if atkMove == Move.Bi:
        if defMove == Move.Def: return True
        if defMove == Move.TianLiJun: return True
        if defMove == Move.Bomb:
            x = defender.bombUses + 1
            if x > 4: x = 4
            threshold = (x - 1) * kDDOne
            return attack_power_units(atkMove, atkXiaoEnhanced) <= threshold
        if is_blocked_by_any_defense(atkMove, atkXiaoEnhanced): return defMove not in {Move.Reflect, Move.Absorb, Move.Cloud, Move.Suicide}
        return False
    if atkMove == Move.Xiao:
        if atkXiaoEnhanced:
            return defMove == Move.JuYan
        if defMove == Move.JuYan: return True
        if defMove in {Move.Def, Move.ThreeDef, Move.PragonDef, Move.VolvoDef, Move.NieXiangDef, Move.TianLiJun}: return True
        if defMove == Move.Bomb:
            x = defender.bombUses + 1
            if x > 4: x = 4
            threshold = (x - 1) * kDDOne
            return attack_power_units(atkMove, atkXiaoEnhanced) <= threshold
        return False
    if atkMove == Move.NieXiang:
        if defMove == Move.NieXiangDef: return True
        if defMove == Move.TianLiJun: return True
        return False
    if defMove == Move.TianLiJun: return True
    if defMove == Move.Bomb:
        x = defender.bombUses + 1
        if x > 4: x = 4
        threshold = (x - 1) * kDDOne
        return attack_power_units(atkMove, atkXiaoEnhanced) <= threshold
    return False


def resolve_no_quantum(p0: PlayerState, c0: PlayerState, pAct: Action, cAct: Action, pEff: Move, cEff: Move) -> Tuple[Outcome, Tuple[int,int]]:
    pXiaoEnhanced = pAct.xiaoEnhanced and pEff == Move.Xiao
    cXiaoEnhanced = cAct.xiaoEnhanced and cEff == Move.Xiao
    # LiQiang immediate wins
    if pAct.triggersLiQiangWin and cAct.triggersLiQiangWin: return (Outcome.Draw, (0,0))
    if pAct.triggersLiQiangWin: return (Outcome.PlayerWin, (0,0))
    if cAct.triggersLiQiangWin: return (Outcome.CpuWin, (0,0))
    # suicides
    if pEff == Move.Suicide and cEff == Move.Suicide: return (Outcome.Draw, (0,0))
    if pEff == Move.Suicide:
        if cEff in {Move.Reflect, Move.Absorb, Move.Cloud}: return (Outcome.PlayerWin, (0,0))
        return (Outcome.CpuWin, (0,0))
    if cEff == Move.Suicide:
        if pEff in {Move.Reflect, Move.Absorb, Move.Cloud}: return (Outcome.CpuWin, (0,0))
        return (Outcome.PlayerWin, (0,0))
    # TianLiJun vs counters
    if pEff == Move.TianLiJun and cEff in {Move.Reflect, Move.Absorb, Move.Cloud}: return (Outcome.CpuWin, (0,0))
    if cEff == Move.TianLiJun and pEff in {Move.Reflect, Move.Absorb, Move.Cloud}: return (Outcome.PlayerWin, (0,0))
    # Reflect immediate kill
    if pEff == Move.Reflect and (not is_unreflectable(cEff)) and is_attack_move(cEff): return (Outcome.PlayerWin, (0,0))
    if cEff == Move.Reflect and (not is_unreflectable(pEff)) and is_attack_move(pEff): return (Outcome.CpuWin, (0,0))

    ddGainP = 0
    ddGainC = 0

    # Absorb logic
    if pEff == Move.Absorb:
        if cEff == Move.Charge or cAct.liQiangAsCharge:
            ddGainP += kDDOne
            return (Outcome.Continue, (ddGainP, ddGainC))
        if is_absorbable_attack(cEff, cXiaoEnhanced):
            ddGainP += dd_cost_units_for_move(c0, cAct.declared if cAct.declared != Move.ZhangXinWei else cAct.effective)
            return (Outcome.Continue, (ddGainP, ddGainC))
    if cEff == Move.Absorb:
        if pEff == Move.Charge or pAct.liQiangAsCharge:
            ddGainC += kDDOne
            return (Outcome.Continue, (ddGainP, ddGainC))
        if is_absorbable_attack(pEff, pXiaoEnhanced):
            ddGainC += dd_cost_units_for_move(p0, pAct.declared if pAct.declared != Move.ZhangXinWei else pAct.effective)
            return (Outcome.Continue, (ddGainP, ddGainC))
    # Cloud similar
    if pEff == Move.Cloud:
        if cEff == Move.Charge or cAct.liQiangAsCharge: return (Outcome.Continue, (ddGainP, ddGainC))
        if is_absorbable_attack(cEff, cXiaoEnhanced): return (Outcome.Continue, (ddGainP, ddGainC))
    if cEff == Move.Cloud:
        if pEff == Move.Charge or pAct.liQiangAsCharge: return (Outcome.Continue, (ddGainP, ddGainC))
        if is_absorbable_attack(pEff, pXiaoEnhanced): return (Outcome.Continue, (ddGainP, ddGainC))
    # XiaoBei interactions
    if pEff == Move.XiaoBei and (cEff == Move.Charge or cAct.liQiangAsCharge): return (Outcome.CpuWin, (0,0))
    if cEff == Move.XiaoBei and (pEff == Move.Charge or pAct.liQiangAsCharge): return (Outcome.PlayerWin, (0,0))
    # Shell/XiaoBei neutrality
    if pEff == Move.Shell and cEff == Move.XiaoBei: return (Outcome.Continue, (0,0))
    if cEff == Move.Shell and pEff == Move.XiaoBei: return (Outcome.Continue, (0,0))
    if pEff == Move.Shell and cEff == Move.Shell: return (Outcome.Continue, (0,0))
    if pEff == Move.XiaoBei and cEff == Move.XiaoBei: return (Outcome.Continue, (0,0))

    pIsAtk = is_attack_move(pEff)
    cIsAtk = is_attack_move(cEff)

    if pIsAtk and cIsAtk:
        pPow = attack_power_units(pEff, pXiaoEnhanced)
        cPow = attack_power_units(cEff, cXiaoEnhanced)
        if pPow == cPow: return (Outcome.Continue, (0,0))
        return (Outcome.PlayerWin, (0,0)) if pPow > cPow else (Outcome.CpuWin, (0,0))
    if pIsAtk and not cIsAtk:
        if blocks_attack(c0, cAct, cEff, pEff, pXiaoEnhanced): return (Outcome.Continue, (0,0))
        return (Outcome.PlayerWin, (0,0))
    if cIsAtk and not pIsAtk:
        if blocks_attack(p0, pAct, pEff, cEff, cXiaoEnhanced): return (Outcome.Continue, (0,0))
        return (Outcome.CpuWin, (0,0))
    return (Outcome.Continue, (0,0))


def select_quantum_outcome(p0: PlayerState, c0: PlayerState, pAct: Action, cAct: Action) -> Tuple[Outcome, int, int]:
    pInts = interpretations(pAct)
    cInts = interpretations(cAct)
    # build cell utilities
    class Cell:
        def __init__(self, out, gp, gc, up, uc):
            self.out = out; self.gp = gp; self.gc = gc; self.up = up; self.uc = uc
    cells = [[None for _ in cInts] for _ in pInts]
    for i, pi in enumerate(pInts):
        for j, cj in enumerate(cInts):
            out, (gp, gc) = resolve_no_quantum(p0, c0, pAct, cAct, pi, cj)
            if out == Outcome.PlayerWin:
                up, uc = 1, -1
            elif out == Outcome.CpuWin:
                up, uc = -1, 1
            elif out == Outcome.Draw:
                up, uc = 0, 0
            else:
                up, uc = 0, 0
            cells[i][j] = Cell(out, gp, gc, up, uc)
    # find pure equilibria where neither player can improve
    equilibria = []
    for i in range(len(pInts)):
        for j in range(len(cInts)):
            up = cells[i][j].up
            uc = cells[i][j].uc
            pBest = True
            for ii in range(len(pInts)):
                if cells[ii][j].up > up:
                    pBest = False; break
            if not pBest: continue
            cBest = True
            for jj in range(len(cInts)):
                if cells[i][jj].uc > uc:
                    cBest = False; break
            if not cBest: continue
            equilibria.append((i,j))
    bi, bj = 0, 0
    if equilibria:
        bi, bj = equilibria[0]
    else:
        bestScore = -10**9
        for i in range(len(pInts)):
            for j in range(len(cInts)):
                score = cells[i][j].up + cells[i][j].uc
                if score > bestScore:
                    bestScore = score; bi, bj = i, j
    chosen = cells[bi][bj]
    return chosen.out, chosen.gp, chosen.gc

def end_of_turn_bomb(s: PlayerState):
    s.bombLayers += s.bombPending[0]
    s.bombPending[0] = s.bombPending[1]
    s.bombPending[1] = s.bombPending[2]
    s.bombPending[2] = 0
    s.bombLayers = clamp_nonneg(s.bombLayers)

@dataclass
class TurnResult:
    outcome: Outcome = Outcome.Continue
    nextP: PlayerState = None
    nextC: PlayerState = None
    ddGainP: int = 0
    ddGainC: int = 0


def simulate_turn(p0: PlayerState, c0: PlayerState, pMove: Move, cMove: Move) -> TurnResult:
    tr = TurnResult()
    tr.nextP = PlayerState(**p0.__dict__)
    tr.nextC = PlayerState(**c0.__dict__)
    pAct = build_action(p0, c0, pMove)
    cAct = build_action(c0, p0, cMove)
    if not is_legal_move(p0, c0, pMove) or not is_legal_move(c0, p0, cMove):
        tr.outcome = Outcome.Continue
        return tr
    # 历强是否“得手”必须基于双方本回合招式都确定后再结算
    compute_liqiang_triggers(p0, c0, pAct, cAct)
    tr.nextP.dd -= pAct.ddCost
    tr.nextC.dd -= cAct.ddCost
    tr.nextP.dd = clamp_nonneg(tr.nextP.dd)
    tr.nextC.dd = clamp_nonneg(tr.nextC.dd)
    tr.nextP.bombLayers -= pAct.bombLayerCost
    tr.nextC.bombLayers -= cAct.bombLayerCost
    tr.nextP.bombLayers = clamp_nonneg(tr.nextP.bombLayers)
    tr.nextC.bombLayers = clamp_nonneg(tr.nextC.bombLayers)
    tr.nextP.lightning -= pAct.lightningCost
    tr.nextC.lightning -= cAct.lightningCost
    tr.nextP.lightning = clamp_nonneg(tr.nextP.lightning)
    tr.nextC.lightning = clamp_nonneg(tr.nextC.lightning)
    tr.nextP.nxCharge -= pAct.nxCost
    tr.nextC.nxCharge -= cAct.nxCost
    tr.nextP.nxCharge = clamp_nonneg(tr.nextP.nxCharge)
    tr.nextC.nxCharge = clamp_nonneg(tr.nextC.nxCharge)
    if pMove == Move.ZhangXinWei: tr.nextP.zhangUsed = True
    if cMove == Move.ZhangXinWei: tr.nextC.zhangUsed = True
    if pMove == Move.LiQiang: tr.nextP.liqUsed = True
    if cMove == Move.LiQiang: tr.nextC.liqUsed = True
    if pMove == Move.Cloud:
        tr.nextP.cloudUses += 1
        tr.nextP.lightning += 1
    if cMove == Move.Cloud:
        tr.nextC.cloudUses += 1
        tr.nextC.lightning += 1
    if pMove == Move.Bomb:
        tr.nextP.bombUses += 1
        tr.nextP.bombPending[1] += 1
    if cMove == Move.Bomb:
        tr.nextC.bombUses += 1
        tr.nextC.bombPending[1] += 1
    if pMove == Move.TianLiJun: tr.nextP.tianUses += 1
    if cMove == Move.TianLiJun: tr.nextC.tianUses += 1
    if pMove == Move.JuYan: tr.nextP.juyanBuff = True
    if cMove == Move.JuYan: tr.nextC.juyanBuff = True
    if pMove == Move.Def: tr.nextP.nxCharge += 1
    if cMove == Move.Def: tr.nextC.nxCharge += 1
    ddGainP = 0
    ddGainC = 0
    out, gp, gc = select_quantum_outcome(p0, c0, pAct, cAct)
    tr.ddGainP = gp
    tr.ddGainC = gc
    tr.nextP.dd += gp
    tr.nextC.dd += gc
    pCharged = (pAct.effective == Move.Charge)
    cCharged = (cAct.effective == Move.Charge)
    pChargeDenied = False
    cChargeDenied = False
    if pCharged and (cAct.effective in {Move.Absorb, Move.Cloud}): pChargeDenied = True
    if cCharged and (pAct.effective in {Move.Absorb, Move.Cloud}): cChargeDenied = True
    if pCharged and not pChargeDenied: tr.nextP.dd += kDDOne
    if cCharged and not cChargeDenied: tr.nextC.dd += kDDOne
    if pAct.effective == Move.TianLiJun and (cCharged): tr.nextC.dd = 0
    if cAct.effective == Move.TianLiJun and (pCharged): tr.nextP.dd = 0
    if pMove == Move.Def:
        if cAct.effective == Move.Bi or (cAct.effective == Move.Xiao and not cAct.xiaoEnhanced): tr.nextP.nxCharge += 1
    if cMove == Move.Def:
        if pAct.effective == Move.Bi or (pAct.effective == Move.Xiao and not pAct.xiaoEnhanced): tr.nextC.nxCharge += 1
    if pMove == Move.Xiao and p0.juyanBuff: tr.nextP.juyanBuff = False
    if cMove == Move.Xiao and c0.juyanBuff: tr.nextC.juyanBuff = False
    if is_high_attack_for_zhang(pAct.effective):
        tr.nextP.hasHighAttackRecord = True
        tr.nextP.lastHighAttack = pAct.effective
    if is_high_attack_for_zhang(cAct.effective):
        tr.nextC.hasHighAttackRecord = True
        tr.nextC.lastHighAttack = cAct.effective
    tr.nextP.lastMove = pMove
    tr.nextC.lastMove = cMove
    end_of_turn_bomb(tr.nextP)
    end_of_turn_bomb(tr.nextC)
    tr.nextP.dd = clamp_nonneg(tr.nextP.dd)
    tr.nextC.dd = clamp_nonneg(tr.nextC.dd)
    tr.outcome = out
    return tr

# Simple interactive test / demonstration
if __name__ == '__main__':
    p = PlayerState()
    c = PlayerState()
    print('初始玩家 DD:', p.dd, '电脑 DD:', c.dd)
    legal_p = list_legal_moves(p, c)
    print('玩家可选招式数量:', len(legal_p))
    # 展示开局 Cloud vs Charge
    tr = simulate_turn(p, c, Move.Cloud, Move.Charge)
    print('Cloud vs Charge -> outcome:', tr.outcome, 'player dd gain units:', tr.ddGainP)
    print('下一步玩家 DD:', tr.nextP.dd, '电脑 DD:', tr.nextC.dd)


# ================================================================
# 启发式局面估值（用于 Hard 近似 GTO 的续局折扣价值）
# ================================================================

def _evaluate_state_heuristic(self: PlayerState, opp: PlayerState) -> float:
    dd_diff = (self.dd - opp.dd) / (kDDOne * 10.0)
    dd_diff = max(-1.0, min(1.0, dd_diff))
    score = 0.55 * dd_diff

    # 一次性技能隐性机会成本：tianUses/liqUsed/zhangUsed 本回合被用掉
    # 后未来可出的策略集严格变小（TianLiJun/LiQiang/ZhangXinWei 不再出）
    # 用掉 = -0.15（一个"弱"小招的平均 EV 成本），对方用掉 = +0.15
    if self.tianUses: score -= 0.15
    if opp.tianUses:  score += 0.15
    if self.liqUsed:  score -= 0.15
    if opp.liqUsed:   score += 0.15
    if self.zhangUsed:score -= 0.12
    if opp.zhangUsed: score += 0.12

    def dmg_potential(s: PlayerState) -> float:
        max_pow = 0
        for m in list_legal_moves(s, PlayerState(dd=10 * kDDOne)):
            if is_attack_move(m):
                xe = False
                if m == Move.Xiao and s.juyanBuff:
                    xe = True
                pow_val = attack_power_units(m, xe)
                if pow_val > max_pow:
                    max_pow = pow_val
        return max_pow / 60.0

    self_pot = dmg_potential(self)
    opp_pot = dmg_potential(opp)
    score += 0.20 * (self_pot - opp_pot)

    self_can_end = False
    opp_can_end = False
    for m in list_legal_moves(self, opp):
        if is_unreflectable(m) and is_attack_move(m):
            self_can_end = True; break
    for m in list_legal_moves(opp, self):
        if is_unreflectable(m) and is_attack_move(m):
            opp_can_end = True; break
    if self_can_end and not opp_can_end:
        score += 0.25
    elif not self_can_end and opp_can_end:
        score -= 0.25

    score = max(-0.98, min(0.98, score))
    return score


# ================================================================
# Regret-matching 求解零和矩阵博弈（近似纳什均衡）
# ================================================================

@dataclass
class MatrixGameSolution:
    player_strategy: Dict[int, float]
    opp_strategy: Dict[int, float]
    value: float


def _regret_matching_solve(A: List[List[float]], iterations: int) -> MatrixGameSolution:
    m = len(A)
    n = len(A[0]) if m else 0
    if m == 0 or n == 0:
        return MatrixGameSolution(player_strategy={}, opp_strategy={}, value=0.0)

    rp = [0.0] * m
    rc = [0.0] * n
    sp = [0.0] * m
    sc = [0.0] * n

    def strat_from_regrets(r):
        sz = len(r)
        total_pos = 0.0
        s = [0.0] * sz
        for i in range(sz):
            if r[i] > 0:
                s[i] = r[i]
                total_pos += r[i]
        if total_pos <= 1e-12:
            return [1.0 / sz] * sz
        return [x / total_pos for x in s]

    for _ in range(iterations):
        p = strat_from_regrets(rp)
        q = strat_from_regrets(rc)
        for i in range(m):
            sp[i] += p[i]
        for j in range(n):
            sc[j] += q[j]
        uP = [0.0] * m
        for i in range(m):
            s = 0.0
            for j in range(n):
                s += A[i][j] * q[j]
            uP[i] = s
        evP = sum(p[i] * uP[i] for i in range(m))
        for i in range(m):
            rp[i] += uP[i] - evP
        uC = [0.0] * n
        for j in range(n):
            s = 0.0
            for i in range(m):
                s += p[i] * A[i][j]
            uC[j] = s
        evC = sum(q[j] * uC[j] for j in range(n))
        for j in range(n):
            rc[j] += evC - uC[j]

    iters_inv = 1.0 / max(1, iterations)
    for i in range(m):
        sp[i] *= iters_inv
    for j in range(n):
        sc[j] *= iters_inv
    sp_sum = sum(sp)
    sc_sum = sum(sc)
    if sp_sum > 0:
        sp = [x / sp_sum for x in sp]
    if sc_sum > 0:
        sc = [x / sc_sum for x in sc]
    v = sum(sp[i] * A[i][j] * sc[j] for i in range(m) for j in range(n))
    ps: Dict[int, float] = {}
    cs: Dict[int, float] = {}
    for i in range(m):
        if sp[i] > 1e-9:
            ps[i] = sp[i]
    for j in range(n):
        if sc[j] > 1e-9:
            cs[j] = sc[j]
    return MatrixGameSolution(player_strategy=ps, opp_strategy=cs, value=v)


# ================================================================
# 近似 GTO 求解器（按当前盘面，单步局部零和博弈 + 启发式续局价值）
# ================================================================

class LocalGTOSolver:
    def __init__(self, gamma: float = 0.96, iterations: int = 2500):
        self.gamma = gamma
        self.iterations = iterations

    def solve(self, player_state: PlayerState, cpu_state: PlayerState,
              report: Optional[callable] = None) -> Tuple[List[Move], List[Move], List[float], List[float], float]:
        p_moves = list_legal_moves(player_state, cpu_state)
        c_moves = list_legal_moves(cpu_state, player_state)
        if not p_moves or not c_moves:
            return p_moves, c_moves, [], [], 0.0

        m = len(p_moves)
        n = len(c_moves)
        A = [[0.0] * n for _ in range(m)]
        for i in range(m):
            for j in range(n):
                tr = simulate_turn(player_state, cpu_state, p_moves[i], c_moves[j])
                if tr.outcome == Outcome.PlayerWin:
                    A[i][j] = 1.0
                elif tr.outcome == Outcome.CpuWin:
                    A[i][j] = -1.0
                elif tr.outcome == Outcome.Draw:
                    A[i][j] = 0.0
                else:
                    cont = _evaluate_state_heuristic(tr.nextP, tr.nextC)
                    A[i][j] = self.gamma * cont

        sol = _regret_matching_solve(A, self.iterations)
        p_probs = [sol.player_strategy.get(i, 0.0) for i in range(m)]
        c_probs = [sol.opp_strategy.get(j, 0.0) for j in range(n)]
        return p_moves, c_moves, p_probs, c_probs, sol.value

    def choose_move_for_cpu(self, player_state: PlayerState, cpu_state: PlayerState,
                            rng: random.Random) -> Move:
        c_moves = list_legal_moves(cpu_state, player_state)
        if not c_moves:
            return Move.Charge
        _, c_legal, _, c_probs, _ = self.solve(player_state, cpu_state)
        if not c_legal:
            return rng.choice(c_moves) if c_moves else Move.Charge
        c_idx_map = {m: i for i, m in enumerate(c_legal)}
        # 首回合/未出招阶段硬过滤：严格劣势一次性动作直接禁止
        # (cpu_state 是 Hard/GTO 自己的状态，player_state 是对手的)
        is_first_turn_ = (cpu_state.lastMove == Move.NoMove
                          and player_state.lastMove == Move.NoMove
                          and cpu_state.dd == 0
                          and player_state.dd == 0)
        dist = []
        for m in c_moves:
            p = c_probs[c_idx_map[m]] if m in c_idx_map else 0.0
            if is_first_turn_ and m in {Move.TianLiJun, Move.LiQiang}:
                p = 0.0
            if m == Move.LiQiang and player_state.lastMove == Move.NoMove:
                p = 0.0  # 对手没出过招，历强 100% 不触发
            dist.append(p)
        total = sum(dist)
        if total <= 1e-12:
            return rng.choice(c_moves)
        r = rng.random() * total
        acc = 0.0
        for m, pr in zip(c_moves, dist):
            acc += pr
            if r <= acc:
                return m
        return c_moves[-1]


# ================================================================
# Easy 启发式策略
# ================================================================

def choose_easy_move(cpu_state: PlayerState, player_state: PlayerState,
                     rng: random.Random) -> Move:
    legal = list_legal_moves(cpu_state, player_state)
    if not legal:
        return Move.Charge

    def has(m):
        return m in legal

    r = rng.random()
    if Move.Shell in legal and r < 0.20:
        return Move.Shell
    if Move.XiaoBei in legal and r < 0.12:
        return Move.XiaoBei
    if Move.FlipVolvo in legal and r < 0.10:
        return Move.FlipVolvo
    if Move.RotateThree in legal and r < 0.10:
        return Move.RotateThree
    if Move.BigBi in legal and r < 0.10:
        return Move.BigBi
    if Move.Volvo in legal and r < 0.10:
        return Move.Volvo
    if Move.Three in legal and r < 0.12:
        return Move.Three
    if Move.Pragon in legal and r < 0.10:
        return Move.Pragon
    if Move.Reflect in legal and r < 0.12:
        return Move.Reflect
    if Move.Suicide in legal and r < 0.05:
        return Move.Suicide

    if Move.NieXiang in legal and r < 0.3:
        return Move.NieXiang
    if cpu_state.nxCharge < 4 and Move.Def in legal and r < 0.35:
        return Move.Def
    if cpu_state.lightning >= 6 and has(Move.FreeRotateThree) and r < 0.3:
        return Move.FreeRotateThree
    if cpu_state.lightning >= 3 and has(Move.FreeThree) and r < 0.25:
        return Move.FreeThree
    if cpu_state.bombLayers >= 4 and has(Move.BombFlipVolvo):
        return Move.BombFlipVolvo
    if cpu_state.bombLayers >= 2 and has(Move.BombVolvo):
        return Move.BombVolvo
    if cpu_state.bombLayers >= 1 and has(Move.BombPragon) and r < 0.4:
        return Move.BombPragon
    if has(Move.Bomb) and r < 0.18:
        return Move.Bomb
    if has(Move.Cloud) and r < 0.15:
        return Move.Cloud
    if has(Move.JuYan) and not cpu_state.juyanBuff and r < 0.15:
        return Move.JuYan
    if has(Move.Absorb) and r < 0.10:
        return Move.Absorb
    if has(Move.TianLiJun) and cpu_state.dd < 5 * kDDOne and r < 0.10:
        return Move.TianLiJun
    if has(Move.Xiao) and r < 0.15:
        return Move.Xiao
    if has(Move.Bi) and r < 0.18:
        return Move.Bi

    preferred = [Move.Charge, Move.Xiao, Move.Bi, Move.Def, Move.ThreeDef,
                 Move.PragonDef, Move.VolvoDef, Move.JuYan, Move.NieXiangDef,
                 Move.Bomb, Move.Cloud, Move.Absorb, Move.LiQiang]
    if Move.ZhangXinWei in legal:
        preferred.insert(0, Move.ZhangXinWei)
    if Move.LiQiang in legal:
        preferred.insert(0, Move.LiQiang)
    for m in preferred:
        if m in legal:
            return m
    return rng.choice(legal)


def value_to_reference_winrate(v: float) -> float:
    w = 0.5 * (v + 1.0)
    return max(0.0, min(1.0, w))

