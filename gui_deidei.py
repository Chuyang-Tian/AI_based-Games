import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random
from deidei_env import (
    Move, Outcome, PlayerState, ALL_MOVES, kDDDen, kDDOne,
    list_legal_moves, simulate_turn, dd_cost_units_for_move,
    is_attack_move, is_unreflectable, is_high_attack_for_zhang,
    choose_easy_move, LocalGTOSolver, value_to_reference_winrate,
)
try:
    from rl_ai import choose_rl_move, model_available as rl_model_available, set_rl_inference_threads
    HAS_RL_AI = True
except ImportError:
    HAS_RL_AI = False
    def rl_model_available(*a, **k): return False
    def choose_rl_move(*a, **k):
        return choose_easy_move(*a, **k)
    def set_rl_inference_threads(*a, **k): return None


MOVE_NAMES_CN = {
    Move.Charge: "攒",
    Move.Bi: "Bi",
    Move.Def: "防御",
    Move.Three: "三雷",
    Move.ThreeDef: "三雷防",
    Move.BigBi: "大Bi",
    Move.Reflect: "反弹",
    Move.Suicide: "自杀",
    Move.Cloud: "云",
    Move.Bomb: "炸药",
    Move.Xiao: "削",
    Move.Pragon: "Pragon",
    Move.PragonDef: "Pragon防",
    Move.Volvo: "沃尔沃",
    Move.VolvoDef: "沃尔沃防",
    Move.RotateThree: "旋转三雷",
    Move.XiaoBei: "小贝",
    Move.FlipVolvo: "翻转沃尔沃",
    Move.Shell: "扇贝",
    Move.Absorb: "吸收",
    Move.NieXiang: "聂湘",
    Move.NieXiangDef: "聂湘防",
    Move.JuYan: "距喦",
    Move.TianLiJun: "田立军",
    Move.ZhangXinWei: "张新伟",
    Move.LiQiang: "历强",
    Move.BombPragon: "炸药·Pragon",
    Move.BombVolvo: "炸药·沃尔沃",
    Move.BombFlipVolvo: "炸药·翻转沃尔沃",
    Move.FreeThree: "雷电·免费三雷",
    Move.FreeRotateThree: "雷电·免费旋转三雷",
}

MOVE_DETAILS_CN = {
    Move.Charge: ("攒 / Charge", "0 DD",
        "【作用】本回合 +1 DD（内部 1 DD = 6 最小单位）。\n"
        "【相克】被「吸收」（你攒的 1 DD 归对手）、「田立军」（你全部 DD 被瞬间清空！）克制；"
        "对手出「小贝」时，出攒能直接打死它。\n"
        "【新手提示】开局基本都出攒，先把 DD 攒到能出攻击的阈值再出招。"),
    Move.Xiao: ("削 / Xiao", "2 单位 = 1/3 DD",
        "【作用】最小的攻击。普通削：任何防御都能挡。\n"
        "⚠️ 距喦 之后的下一次削 = 「强化削」：除了 距喦 自己，其它所有防御（含 Def！）全都挡不住！\n"
        "【相克】被任何防御 / 反弹 / 吸收 / 云 克。"),
    Move.Bi: ("Bi", "6 单位 = 1 DD",
        "【作用】最基础的 1 DD 进攻招。\n"
        "【能挡 Bi 的人】防御 / 距喦 / 田立军 / 炸药（炸药次数够）。\n"
        "⚠️ 4 个专属防御（Pragon防/沃尔沃防/三雷防/聂湘防）：全都挡不住 Bi！\n"
        "【新手提示】新手容易错出 Pragon 防去挡 Bi，挡不住直接死。"),
    Move.Def: ("防御 / Def", "0 DD",
        "【能挡】普通削 + Bi（仅此两类！）\n"
        "⚠️ 挡不住：Pragon / 三雷 / 沃尔沃 / 大Bi / 聂湘 / 炸药攻击 / 免费三雷 / 强化削……任何 2DD 以上或带 buff 的攻击！\n"
        "【附带】每次 +1 聂湘充能，成功格挡再 +1。攒到 4 点就能放聂湘（免费大招）。\n"
        "【新手提示】大落后（落后 2 DD 以上）别出太多防御——小招挡得住，Pragon / 大Bi 直接拍死你。"),
    Move.Three: ("三雷 / Three", "18 单位 = 3 DD",
        "【作用】中高阶攻击，无视普通防御 Def！\n"
        "【能挡】三雷防 / 田立军 / 反弹 / 吸收（吸收范围内）。"),
    Move.ThreeDef: ("三雷防 / ThreeDef", "0 DD",
        "【独有价值】对手能出「三雷类（三雷 / 免费三雷 / 旋转三雷 / 免费旋转三雷）」时才有意义——Def 挡不住三雷类。"
        "若对手三雷类根本放不出来 → 出这个严格劣于 防御（防御还能多挡一个 Bi！）。\n"
        "【能挡】普通削 + Bi + 三雷类。"),
    Move.BigBi: ("大Bi / BigBi", "30 单位 = 5 DD",
        "【作用】终极高伤攻击。⚠️ 除了「田立军」，其它所有防御 / 4 个专属防御 全都挡不住！（很反直觉，一定要记住）\n"
        "【能挡】田立军（唯一）、反弹、吸收。\n"
        "【新手提示】对手 DD ≥ 5 时：你至少留 12% 概率出田立军防 BigBi，不然对手放一次就没了。"),
    Move.Reflect: ("反弹 / Reflect", "6 单位 = 1 DD",
        "【作用】对手出「可反弹的攻击」时：你直接赢！\n"
        "【可反弹的攻击】Xiao / Bi / Pragon / 三雷 / 沃尔沃 / 大Bi / 聂湘 / 炸药攻击类 / 免费三雷（除了 扇贝/小贝 这俩 is_unreflectable，其它攻击都能反弹）。\n"
        "【克反弹的招】自杀 / 量子态（旋转三雷 / 翻转沃尔沃 / 免费旋转三雷，它们最有利分支 = 自杀克反弹）。\n"
        "⚠️ 对手这回合一个攻击都出不了（比如 0 DD + 没炸药/雷电层）→ 出反弹 = 纯送 1 DD，电脑会被自动 ban 掉这种反直觉情况。"),
    Move.Suicide: ("自杀 / Suicide", "0 DD",
        "【作用】专克 反弹 / 吸收 / 云（这三个遇到自杀都直接输）！\n"
        "【副作用】对手不是这三类 → 你直接输（等于送人头）。\n"
        "双方同时自杀 → 平局。"),
    Move.Absorb: ("吸收 / Absorb", "6 单位 = 1 DD",
        "【作用】两重收益：\n"
        "  1) 对「攒」：你 +1 DD，对手攒失效（相当于你同时放了 2 个攒）\n"
        "  2) 对吸收范围内攻击（Xiao / Bi / Pragon / 三雷 / 大Bi / 免费三雷）→ 视为完美防 + 你获得对手消耗的 DD！\n"
        "⚠️ 吸收不到：沃尔沃类 / 炸药攻击 / 旋转三雷 / 翻转沃尔沃 / 聂湘 / 扇贝 / 小贝 / 强化削（距喦后削）。\n"
        "【克吸收的】自杀 / 量子态 / 扇贝 / 小贝。"),
    Move.Cloud: ("云 / Cloud", "首次 0 DD，之后每次 6 单位 = 1 DD",
        "【作用】类似吸收但吸到的 DD 无人得；每次 +1 雷电层。\n"
        "  • 雷电层 = 3 → 放「雷电·免费三雷」（0 DD 三雷，无视 Def）\n"
        "  • 雷电层 = 6 → 放「雷电·免费旋转三雷」（0 DD 量子旋转三雷，专克反弹/吸收/云）\n"
        "【克云的】自杀（云被自杀直接打死）。"),
    Move.Bomb: ("炸药 / Bomb", "6 单位 = 1 DD",
        "【作用】延迟型资源。槽位顺序 = A → B → C（放的这回合 = A；下一回合 = B；B 回合末直接进「炸药层」可用了！不是 C！）\n"
        "即：T 放炸药 → T+2 初就有 1 层炸药层。\n"
        "炸药层兑换：\n"
        "  • 1 层 → 炸药·Pragon（0 DD Pragon，Def 挡不住！）\n"
        "  • 2 层 → 炸药·沃尔沃（0 DD 沃尔沃）\n"
        "  • 4 层 → 炸药·翻转沃尔沃（0 DD 量子翻转沃尔沃，克反弹/吸收/云）\n"
        "【附带】放炸药的这回合还能「挡强度 ≤ 炸药次数 - 1 的攻击」（最多 X=4 时相当于 4 层盾）。"),
    Move.BombPragon: ("炸药·Pragon", "消耗 1 层炸药（0 DD）",
        "【作用】0 DD 放 Pragon 级攻击，Def 挡不住，性价比爆炸。\n"
        "【能挡】Pragon防 / 田立军 / 反弹 / 吸收。"),
    Move.BombVolvo: ("炸药·沃尔沃", "消耗 2 层炸药（0 DD）",
        "【作用】0 DD 放沃尔沃级攻击，无视 Def。\n"
        "【能挡】沃尔沃防 / 田立军 / 反弹（吸收吸不到沃尔沃）。"),
    Move.BombFlipVolvo: ("炸药·翻转沃尔沃", "消耗 4 层炸药（0 DD）",
        "【作用】0 DD 放量子翻转沃尔沃（沃尔沃/自杀二选一取最有利），克反弹/吸收/云。\n"
        "【能挡】沃尔沃防（量子态分支）。"),
    Move.FreeThree: ("雷电·免费三雷", "消耗 3 雷电层（0 DD）",
        "【作用】0 DD 放三雷级攻击，无视 Def。\n"
        "【能挡】三雷防 / 田立军 / 反弹 / 吸收。"),
    Move.FreeRotateThree: ("雷电·免费旋转三雷", "消耗 6 雷电层（0 DD）",
        "【作用】0 DD 放量子旋转三雷（三雷/自杀二选一取最有利），专克反弹/吸收/云。\n"
        "【能挡】三雷防。"),
    Move.Pragon: ("Pragon", "12 单位 = 2 DD",
        "【作用】低阶高威力，Def 挡不住。\n"
        "【能挡】Pragon防 / 田立军 / 反弹 / 吸收 / 炸药（次数够）。"),
    Move.PragonDef: ("Pragon防 / PragonDef", "0 DD",
        "【独有价值】对手能出 Pragon 类（Pragon / 炸药·Pragon）时才有意义——Def 挡不住 Pragon，所以需要它。"
        "若对手根本出不来 Pragon → 严格劣于 防御（防御还能挡 Bi）。\n"
        "【能挡】普通削 + Bi + Pragon 类。"),
    Move.Volvo: ("沃尔沃 / Volvo", "24 单位 = 4 DD",
        "【作用】高阶攻击，Def 无视。\n"
        "【能挡】沃尔沃防 / 田立军 / 反弹。⚠️ 吸收吸收不到沃尔沃。"),
    Move.VolvoDef: ("沃尔沃防 / VolvoDef", "0 DD",
        "【独有价值】对手能出沃尔沃类（沃尔沃 / 炸药沃尔沃 / 翻转沃尔沃 / 炸药翻转沃尔沃）时才有意义。\n"
        "【能挡】普通削 + Bi + 沃尔沃类。"),
    Move.RotateThree: ("旋转三雷 / RotateThree", "36 单位 = 6 DD",
        "【作用】量子态攻击：结算时按「三雷 / 自杀」两个分支取对你最有利的那个。"
        "专克 反弹 / 吸收 / 云（因为自杀分支克它们）。\n"
        "【能挡】三雷防（三雷分支）。"),
    Move.XiaoBei: ("小贝 / XiaoBei", "42 单位 = 7 DD",
        "【作用】高阶攻击，有个致命弱点：被对手的「攒」直接打死（小贝克不了攒！）。\n"
        "【特性】和 扇贝 同级，可与 扇贝 抵消。反弹反弹不了小贝（is_unreflectable）。"),
    Move.FlipVolvo: ("翻转沃尔沃 / FlipVolvo", "48 单位 = 8 DD",
        "【作用】量子态攻击：「沃尔沃 / 自杀」二选一取最有利，克 反弹 / 吸收 / 云。\n"
        "【能挡】沃尔沃防。⚠️ 吸收吸收不到。"),
    Move.Shell: ("扇贝 / Shell", "60 单位 = 10 DD",
        "【作用】终极招式。无视所有防御、反弹反弹不了、吸收吸收不到、云也克不了。\n"
        "【唯一解法】你也出 扇贝 或 小贝 抵消；或者你出攒时对手出小贝（小贝被攒克）。\n"
        "【新手提示】DD 到 10 放扇贝基本就赢了，除非对面也扇贝。"),
    Move.NieXiang: ("聂湘 / NieXiang", "聂湘充能 = 4（0 DD）",
        "【作用】免费大招，需要 防御 攒 4 次充能才合法。威力在三雷与沃尔沃之间（约 3.5 DD）。吸收吸收不到聂湘。\n"
        "【能挡】聂湘防 / 田立军 / 反弹。"),
    Move.NieXiangDef: ("聂湘防 / NieXiangDef", "0 DD",
        "【独有价值】对手聂湘充能 ≥ 4（聂湘才放得出来）时才有意义。\n"
        "【能挡】普通削 + Bi + 聂湘。"),
    Move.JuYan: ("距喦 / JuYan", "0 DD",
        "【作用】两用：\n"
        "  1) 防御：能挡 普通削 / 强化削（距喦后的削，只有距喦能挡！）/ Bi。\n"
        "  2) 进攻 buff：用了 距喦 之后 → 下回合削变「强化削」（除了距喦，没人能挡！直接穿防削死）。\n"
        "【新手提示】距喦 + 强化削 = 连招。放完距喦 下回合就想办法出削。"),
    Move.TianLiJun: ("田立军 / TianLiJun", "首次 0 DD，之后每次 3 单位 = 0.5 DD",
        "【作用】全能防御 + 清空对手 DD：\n"
        "  • 对 攒 → 对手 DD 全部清零（神级反制！对手 5 DD 快出大Bi 时你放田立军 → 清零从头再来）\n"
        "  • 对 攻击 → 除了扇贝/小贝 以外的攻击全能完美挡（大Bi 只有田立军能挡！）\n"
        "⚠️ 致命弱点！遇 反弹 / 吸收 / 云 → 田立军方 直接输！这是游戏最反直觉的一条，一定要背下来。\n"
        "【次数】每局可放 N 次（UI 会显示「田立军次数」）。"),
    Move.ZhangXinWei: ("张新伟 / ZhangXinWei", "0 DD（但你 DD 不能低于复制那招的成本）",
        "【作用】每局仅 1 次：复制对手**上回合**放的「Pragon 级以上高阶攻击」（即 Pragon / 三雷 / 沃尔沃 / 大Bi / 聂湘 / 量子态 / 扇贝 / 小贝 / 炸药攻击 / 免费三雷 类）。"
        "若对手没放过 → 不合法（按钮都不出现）。\n"
        "【新手提示】按钮上会写「复制:XX」一眼懂。注意：「张新伟(复制Bi) + 接着出 Bi」→ 两招实际相同，对手出历强 = 直接触发 LiQiang 判赢！"),
    Move.LiQiang: ("历强 / LiQiang", "0 DD",
        "【作用】每局仅 1 次：若对手本回合招 = 上回合招 → 你直接赢！否则 = 普通攒（+1 DD）。\n"
        "⚠️ 「对手上回合 = 张新伟复制A」+「对手本回合 = A」→ 也算连续，历强判赢（因为实际动作等效）。\n"
        "【新手提示】对手连放两次同样的大招（Bi/Bi，Pragon/Pragon，张新伟Bi + Bi），历强一出就赢。\n"
        "⚠️ 第 1 回合对手 NoMove → 历强必不触发，直接被自动 ban。"),
}


def _format_move_details(m: Move) -> str:
    t = MOVE_DETAILS_CN.get(m)
    if t is None:
        return f"■ {m.name}\n成本：?\n\n暂无详细说明，点“查看完整规则”。"
    title, cost, body = t
    return f"■ {title}\n成本：{cost}\n\n{body}"


def move_label(m: Move, p: PlayerState) -> str:
    base = MOVE_NAMES_CN.get(m, m.name)
    if m == Move.ZhangXinWei and p.hasHighAttackRecord:
        base += f"\n(复制:{MOVE_NAMES_CN.get(p.lastHighAttack, p.lastHighAttack.name)})"
    if m == Move.Xiao and p.juyanBuff:
        base += "\n(距喦后=强化削)"
    return base



def format_dd_units(units: int) -> str:
    if units < 0:
        units = 0
    whole = units // kDDDen
    rem = units % kDDDen
    if rem == 0:
        return str(whole)
    g = math_gcd(rem, kDDDen)
    rem //= g
    den = kDDDen // g
    if whole == 0:
        return f"{rem}/{den}"
    return f"{whole}+{rem}/{den}"


def math_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def parse_dd_units(s: str) -> int:
    s = s.strip()
    if s == "":
        return 0
    total = 0
    parts = s.split('+')
    for part in parts:
        part = part.strip()
        if '/' in part:
            a, b = part.split('/')
            a = a.strip(); b = b.strip()
            try:
                ai = int(a); bi = int(b)
            except Exception as e:
                raise ValueError(f'无效分数: {e}')
            if ai < 0 or bi <= 0:
                raise ValueError('无效分数')
            if (ai * kDDDen) % bi != 0:
                raise ValueError('分数无法表示为1/6的倍数')
            total += (ai * kDDDen) // bi
        else:
            try:
                wi = int(part)
            except Exception as e:
                raise ValueError(f'无效整数: {e}')
            if wi < 0:
                raise ValueError('负数DD')
            total += wi * kDDOne
    return total


PRECISION_PROFILES = {
    "快速": {"gamma": 0.94, "iter": 2000},
    "标准": {"gamma": 0.97, "iter": 5000},
    "高":   {"gamma": 0.99, "iter": 12000},
}

PRECISION_HINT = {
    "快速": "2秒出结果，GTO近似精度一般，快速参考用",
    "标准": "5-8秒出结果，精度和耗时平衡，推荐默认",
    "高":   "15-30秒出结果，接近真GTO，研究均衡用",
}

DIFFICULTY_LABEL = {
    "Easy":     "简单 AI（启发式，新手友好，会犯可剥削的错）",
    "Hard":     "普通 AI（每回合近似GTO无剥削混合策略）",
    "RL Hard":  "专家 AI（PPO 自博弈 853 万步训练，接近人类顶级水平）",
}
DIFFICULTY_HINT_SHORT = {
    "Easy":    "Easy=简单AI  随便玩熟悉招式；Hard=普通AI  按GTO出  不会被剥削；",
    "Hard":    "RL Hard=专家AI  用训练好的模型出招，最强",
    "RL Hard": "需要 rl_checkpoints\\latest.zip（已自带）。推理线程：省电=CPU占用低，平衡=默认，极速=多核拉满推理更快",
}


def make_gto_solver(prec_key: str) -> LocalGTOSolver:
    cfg = PRECISION_PROFILES.get(prec_key, PRECISION_PROFILES["标准"])
    return LocalGTOSolver(gamma=cfg["gamma"], iterations=cfg["iter"])


RULES_TEXT = """═══════════════════════════════════════════════════════════════════════
  DeiDei （叠叠） 完整规则手册  ——  新手 1 分钟入门 + 老手查表
═══════════════════════════════════════════════════════════════════════

【🎮 这是什么游戏】
类似"石头剪刀布"的回合制博弈，但你有一个持续增长的资源池：
  • 每回合双方**同时出招**；任意攻击/反弹得手立刻判胜负。
  • 同类攻击相遇 → 抵消（消耗不返）；不同类攻击 → 强度高者胜。
  • 新手第一次玩：选"简单 AI"玩 5 局，看每个按钮的"右键"说明就会了。
    （招式按钮 鼠标右键 = 单招说明；左上角"完整规则"= 总规则）

───────────────────────────────────────────────────────────────────────
【1. 资源机制（DD · 炸药层 · 雷电层 · 聂湘充能 · 距喦 buff）】
───────────────────────────────────────────────────────────────────────
DD（主资源，攒出来）：
  1 个 DD = 内部 6 最小单位。
    削 = 2 单位 = 1/3 DD
    Bi = 6 单位 = 1 DD     Pragon = 12 = 2 DD     三雷 = 18 = 3 DD
    沃尔沃 = 24 = 4 DD     旋转三雷 = 36 = 6 DD   大Bi = 30 = 5 DD
    扇贝 = 60 = 10 DD

炸药层（延迟 1 回合，B 回合可用！即 A-B-C 的中间就生效）：
  • T 回合放「炸药」→ 延迟层 pending = [A, B, C] 放在 B 槽
  • T+1 末自动 → 进 炸药层 += 1   （⚠️ 之前的老版本是 C 槽才进，现已修！）
  • T+2 初就有 1 层炸药，可兑换：
      1 层 → 炸药·Pragon   (0 DD Pragon  Def 挡不住!)
      2 层 → 炸药·沃尔沃   (0 DD 沃尔沃)
      4 层 → 炸药·翻转沃尔沃 (0 DD 量子态 克反弹/吸收/云)
  • 放「炸药」的当回合，还能当盾用：第 X 次炸药 = 可挡强度 ≤ X-1 的攻击

雷电层（云 每次 +1）：
  3 层 → 雷电·免费三雷       （0 DD 三雷，无视 Def）
  6 层 → 雷电·免费旋转三雷   （0 DD 量子旋转三雷，克反弹/吸收/云）

聂湘充能（防御每次 +1，成功格挡再 +1）：
  攒到 4 点 → 可放「聂湘」（约 3.5 DD 免费大招；吸收吸收不到）

距喦 buff（用一次距喦后 下回合削 = 强化削）：
  强化削：除了 距喦 自己，其它所有防御（含 Def！）全都挡不住！（穿防）

───────────────────────────────────────────────────────────────────────
【2. 动作 5 大类（快速索引）】
───────────────────────────────────────────────────────────────────────
① 攒资源类：     攒（Charge，+1 DD）
② 普通攻击类：   削 / Bi / Pragon / 三雷 / 沃尔沃 / 大Bi / 旋转三雷
                 / 小贝 / 翻转沃尔沃 / 扇贝 / 聂湘
                 + 3 种"0 DD 大招"：炸药·Pragon / 炸药·沃尔沃 / 炸药·翻转沃尔沃
                 + 2 种"雷电大招"：雷电·免费三雷 / 雷电·免费旋转三雷
③ 防御类：       防御 / 距喦 / 田立军  +  4 个专属防御
                 （Pragon防 / 沃尔沃防 / 三雷防 / 聂湘防）
④ 反制类：       反弹 / 吸收 / 云  / 自杀
⑤ 特殊一次性：   张新伟（复制上高阶攻击，1局1次）
                 历强（抓对手连出=直接赢，1局1次）

───────────────────────────────────────────────────────────────────────
【3. 胜负速判 + 最容易搞错的相克表】
───────────────────────────────────────────────────────────────────────
3.1 反弹 / 吸收 / 云 的"自杀克它们"三连：
    自杀 克 反弹/吸收/云（三者遇到自杀直接输）。
3.2 田立军的致命弱点（新手最常送人头的 1 条！背下来）：
    ⚠️ 田立军 遇 反弹/吸收/云 → 田立军方 直接输！
    反过来，田立军对其它：
      • 对 攒 → 清空对手 DD 全部
      • 对 攻击（除扇贝/小贝）→ 完美防
3.3 历强触发（连续相同）：
    对手 本回合招 = 上回合招 → 你放历强 = 直接赢；否则 = 普通攒。
    ⚠️ 张新伟(复制A) + 接着 A 也等效"连续A"，也触发历强。
    ⚠️ 第 1 回合对手 NoMove → 历强必不触发，被自动 ban。
3.4 张新伟复制（1局1次）：
    只能复制对手上回合放过的"Pragon 级以上攻击"（Pragon/三雷/沃尔沃/
    大Bi/聂湘/量子态/扇贝/小贝/炸药攻击/免费三雷 等）。没就不能放。
3.5 反弹能弹谁？
    除了 扇贝 / 小贝（is_unreflectable），其它攻击全都能弹，弹中即赢。
    反弹反被 自杀 / 量子态（旋转三雷/翻转沃尔沃/免费旋转三雷）克。
3.6 量子态（旋转三雷/翻转沃尔沃/免费旋转三雷/炸药翻转沃尔沃）：
    结算时在两个分支里取对你最有利的一个，天然克 反弹/吸收/云。
3.7 扇贝终极：
    防御全无视、反弹弹不到、吸收吸不到、云克不了。
    只有 扇贝/小贝 能抵消；或对手出攒 你出小贝（贝克不了攒）。

───────────────────────────────────────────────────────────────────────
【4. 防御到底能挡什么？一张新手简表（非常重要！）】
───────────────────────────────────────────────────────────────────────
防御招式        能挡的攻击                          挡不住（会被直接打死！）
───────────────────────────────────────────────────────────────────────
防御 Def        普通削 + Bi                         Pragon/三雷/沃尔沃/大Bi/聂湘
                                                  炸药攻击/免费三雷/强化削/量子态...
距喦 JuYan      普通削 + 强化削 + Bi                除上面外，其它同 Def
田立军          普通削 + 强化削 + Bi + Pragon       扇贝 / 小贝（以及反弹/吸收/云
                + 三雷 + 沃尔沃 + 大Bi + 聂湘       对它时田立军反而输！）
                + 所有专属攻击（完美防）
───────────────────────────────────────────────────────────────────────
Pragon防        普通削 + Bi + Pragon + 炸药Pragon    其它所有 2 DD+ 攻击
沃尔沃防        普通削 + Bi + 沃尔沃类               其它
三雷防          普通削 + Bi + 三雷类（含免费/旋转）   其它
聂湘防          普通削 + Bi + 聂湘                   其它
───────────────────────────────────────────────────────────────────────
★ 新手直觉：
  • 对手 0 DD → 防御/4 个专属防御 全没价值（连 Bi 都出不来），自动被 ban。
  • 对手 1~2 DD → 防御 + 距喦 为主，Pragon 合法时补 Pragon防。
  • 对手 ≥ 3 DD → 必须补田立军 + 合法专属防御（Def 挡不住 Pragon/三雷了）
  • 对手 ≥ 5 DD → 田立军至少 12%（大Bi只有田立军能挡！）
  • 对手合法攻击集合 不含可反弹攻击 → 反弹 = 纯送 1 DD，自动 ban

───────────────────────────────────────────────────────────────────────
【5. 玩家常见误区 Top 5（高手也犯的错，顺手列了）】
───────────────────────────────────────────────────────────────────────
❌ 1. 大落后（0 vs 5 DD）还狂点"防御"：
     防御挡不住大Bi/Pragon/三雷/沃尔沃 = 白给。要补田立军 + 专属防御。
❌ 2. 4 个专属防御 当通用防：
     它们连 Bi 都挡不住！没对应攻击出 = 严格劣于 防御（还少挡个 Bi）。
❌ 3. 田立军 vs 反弹：
     田立军方直接输（见 3.2）。
❌ 4. 炸药以为要 3 回合（A→B→C 末尾）：
     现在 B 回合末就进炸药层 = 你 T 放炸药，T+2 初就能出炸药Pragon
     （早了 1 回合，已经修了）。
❌ 5. 张新伟 复制 A 再出 A，对手出历强：
     你以为不会触发历强？实际上两招是连续等效 A → 触发历强直接输。

───────────────────────────────────────────────────────────────────────
【6. 3 个 AI 难度怎么选 + GTO 是什么】
───────────────────────────────────────────────────────────────────────
简单 AI（Easy）：
    纯启发式。新手练手熟悉招，会犯大量错，可随便剥削。
普通 AI（Hard = 近似 GTO）：
    每回合按当前局面做 迭代式近似 GTO 求解混合策略。
    "GTO" = 博弈论「无剥削纳什均衡」：长期玩无论对手多聪明，
    你按这个概率混合出招，不吃亏。
    精度：快速(2k迭代) / 标准(5k，默认推荐) / 高(12k，研究用)
专家 AI（RL Hard = RL 自博弈 853 万步）：
    用 PPO + 自对战 从 0 训练 853 万步的策略网络，
    加人类专家规则硬约束（首回合 ban / 落后防御 / 反射 cap / 连招 boost）
    → 接近人类顶级水平。
    需要 rl_checkpoints\\latest.zip（打包已自带）。
    推理线程：省电(默认低占用) / 平衡(推荐) / 极速(拉满多核)

───────────────────────────────────────────────────────────────────────
【7. 忘记了某招是啥怎么办？两种查法】
───────────────────────────────────────────────────────────────────────
  (1) 对战界面的任何招式按钮 → **鼠标右键** → 弹这招的详细说明（成本、
      作用、克什么、被什么克、新手坑提示）。
      ★ 推荐新手就用这个，见到不懂再查，学习成本最低。
  (2) 点左上角的"查看完整规则" → 你现在打开的这个总手册。
  (3) 不确定会不会赢 → "查看当前局面 GTO" 按钮：
      给你该局面的近似无剥削混合出招 + 参考胜率。

═══════════════════════════════════════════════════════════════════════
  玩得开心 :)
═══════════════════════════════════════════════════════════════════════
"""


class DeideiGUI:
    def __init__(self, root):
        self.root = root
        root.title('DeiDei 叠叠对战 — 左键出招 / 右键查说明')

        self.rng = random.Random()
        self.game_active = False
        self.round_no = 1
        self.player = PlayerState()
        self.cpu = PlayerState()
        self.difficulty = "Easy"
        self.precision = "标准"
        self.rl_cpu_mode = "平衡"
        self.gto = make_gto_solver(self.precision)
        self._first_query_help_shown = False
        self._welcome_shown = False

        # ========== BO（Best of N）赛制状态 ==========
        self.bo_n = 1                     # N 局 N 胜（1/3/5/11/35/自定义奇数）
        self.bo_win_target = 1            # 先赢多少局 = 赢整个BO（= bo_n//2 + 1）
        self.bo_player_wins = 0           # 你赢了几局
        self.bo_cpu_wins = 0              # 电脑赢了几局
        self.bo_current_game = 0          # 当前进行中/刚结束的是第几个小局（1-based，0=未开始）
        self.bo_match_active = False      # 整个BO是否进行中（False=用户还没点开始，或BO已结束）
        self._bo_start_btn_text_default = "开始新对局"
        self._bo_label_map = {            # 下拉里显示的中文 <-> bo_n 内部值（BO1默认）
            "单局（BO1）": 1,
            "短盘 BO3": 3,
            "短盘 BO5": 5,
            "中盘 BO11": 11,
            "长盘 BO35": 35,
            "自定义 N…": -1,
        }
        self._bo_label_inv = {v: k for k, v in self._bo_label_map.items() if v != -1}
        self.bo_var = None                # 下拉 StringVar
        self._bo_start_btn = None         # 「开始新对局」按钮引用（根据BO状态动态改文案）
        self._bo_score_lbl = None         # BO 比分面板 Label（实时更新）

        outer = ttk.Frame(root, padding=8)
        outer.pack(fill='both', expand=True)

        nb = ttk.Notebook(outer)
        nb.pack(fill='both', expand=True)

        self.tab_game = ttk.Frame(nb, padding=8)
        self.tab_sim = ttk.Frame(nb, padding=8)
        nb.add(self.tab_game, text="对战模式（人 vs 电脑）")
        nb.add(self.tab_sim, text="模拟模式（手动双方）")

        self._build_game_tab(self.tab_game)
        self._build_sim_tab(self.tab_sim)

    # ============================================================
    # 对战模式 UI
    # ============================================================
    def _build_game_tab(self, parent):
        top = ttk.LabelFrame(parent, text="设置", padding=8)
        top.pack(fill='x')

        self.difficulty_label_var = tk.StringVar(value=DIFFICULTY_LABEL["Easy"])
        ttk.Label(top, text="AI对手难度:").grid(column=0, row=0, sticky='w')
        self.diff_var = tk.StringVar(value="Easy")
        _diff_values = ["Easy", "Hard"]
        if HAS_RL_AI:
            _diff_values.append("RL Hard")
        self._diff_combo = ttk.Combobox(top, textvariable=self.diff_var, values=_diff_values,
                                        width=14, state='readonly')
        self._diff_combo.grid(column=1, row=0, padx=(2, 10))
        self._diff_combo.bind("<<ComboboxSelected>>", lambda e: self._on_diff_changed())

        ttk.Label(top, text="普通AI精度(GTO迭代):").grid(column=2, row=0, sticky='w')
        self.prec_var = tk.StringVar(value="标准")
        self._prec_combo = ttk.Combobox(top, textvariable=self.prec_var, values=list(PRECISION_PROFILES.keys()),
                                        width=6, state='readonly')
        self._prec_combo.grid(column=3, row=0, padx=(2, 10))
        self._prec_label = ttk.Label(top, text=PRECISION_HINT["标准"], foreground="#555",
                                     wraplength=340, justify='left')
        self._prec_label.grid(column=2, row=2, columnspan=2, sticky='w', pady=(2, 0))
        self._prec_combo.bind("<<ComboboxSelected>>", lambda e: self._on_prec_changed())

        if HAS_RL_AI:
            ttk.Label(top, text="专家AI推理线程:").grid(column=2, row=1, sticky='w', pady=(6, 0))
            self.rl_cpu_mode_var = tk.StringVar(value="平衡")
            _cpu_values = ["省电", "平衡", "极速"]
            self._rl_cpu_combo = ttk.Combobox(top, textvariable=self.rl_cpu_mode_var,
                                              values=_cpu_values, width=6, state='readonly')
            self._rl_cpu_combo.grid(column=3, row=1, padx=(2, 10), pady=(6, 0))
            self._rl_cpu_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_rl_cpu_mode())
        else:
            self.rl_cpu_mode_var = None

        # ====== 新增：赛制（BO N 选 N 胜）======
        ttk.Label(top, text="赛制:").grid(column=4, row=0, sticky='w')
        self.bo_var = tk.StringVar(value="单局（BO1）")
        _bo_values = list(self._bo_label_map.keys())  # [BO1, BO3, BO5, BO11, BO35, 自定义N]
        self._bo_combo = ttk.Combobox(top, textvariable=self.bo_var, values=_bo_values,
                                      width=14, state='readonly')
        self._bo_combo.grid(column=5, row=0, padx=(2, 8))
        self._bo_combo.bind("<<ComboboxSelected>>", lambda e: self._on_bo_changed())
        self._bo_help_lbl = ttk.Label(top, text="单局：一局定胜负", foreground="#555",
                                      wraplength=220, justify='left')
        self._bo_help_lbl.grid(column=4, row=2, columnspan=2, sticky='w', pady=(2, 0))

        self._bo_start_btn = ttk.Button(top, text=self._bo_start_btn_text_default,
                                        command=self.start_new_game)
        self._bo_start_btn.grid(column=6, row=0, padx=6, rowspan=3, sticky='nsew')
        ttk.Button(top, text="完整规则手册", command=self.show_rules).grid(
            column=7, row=0, padx=6, rowspan=3, sticky='nsew')

        # ===== BO 比分面板（BO>=3时显示，BO1隐藏）=====
        self._bo_score_frm = ttk.LabelFrame(parent, text="BO 赛制比分", padding=6)
        self._bo_score_lbl = ttk.Label(self._bo_score_frm, text="",
                                       font=("Segoe UI", 11, "bold"), justify='left')
        self._bo_score_lbl.pack(anchor='w')
        self._bo_reset_btn = ttk.Button(self._bo_score_frm, text="重置本次 BO（比分清零）",
                                        command=self._reset_bo_match, width=28)
        self._bo_reset_btn.pack(side='right')
        # 默认 BO1 不显示比分面板
        self._bo_score_frm.pack_forget()
        self._update_bo_score_ui()

        # status header
        self.status_frm = ttk.LabelFrame(parent, text="当前盘面", padding=8)
        self.status_frm.pack(fill='x', pady=6)
        self.status_lbl = ttk.Label(self.status_frm, text="（尚未开始对局）",
                                     font=("Segoe UI", 10, "bold"), justify='left')
        self.status_lbl.pack(anchor='w')

        # player move buttons + history
        body = ttk.Frame(parent)
        body.pack(fill='both', expand=True)

        left = ttk.LabelFrame(body, text="你要出什么（左键出招 / 鼠标右键=这招说明）", padding=8)
        left.pack(side='left', fill='both', expand=True, padx=(0, 4))

        self.move_btns_frame = ttk.Frame(left)
        self.move_btns_frame.pack(fill='both', expand=True)

        gbuts = ttk.Frame(left)
        gbuts.pack(fill='x', pady=(8, 0))
        ttk.Button(gbuts, text="查看当前局面你的GTO（含参考胜率）",
                   command=self.show_gto_current).pack(side='left')
        ttk.Button(gbuts, text="输入任意状态查询GTO…",
                   command=self.query_gto_state).pack(side='left', padx=6)

        right = ttk.LabelFrame(body, text="对局记录 / 新手提示", padding=8)
        right.pack(side='left', fill='both', expand=True, padx=(4, 0))
        self.log = scrolledtext.ScrolledText(right, width=68, height=26, wrap='word')
        self.log.pack(fill='both', expand=True)
        self._log("【欢迎】DeiDei 叠叠对战\n")
        self._log("   新手 30 秒上手：\n")
        self._log("   ① 先在上方选 AI 难度（默认简单AI=新手友好）\n")
        self._log("   ② 点【开始新对局】→ 在左下按钮上出招：左键出 / 右键=查这招说明\n")
        self._log("   ③ 不知道对面会不会出大Bi/Pragon 剥削你？点【查看当前局面 GTO】→ 给无剥削均衡策略\n")
        self._log("   ④ 完整规则/新手坑/相克表：左上角【完整规则手册】。\n\n")

    # ============================================================
    # 模拟模式 UI（保留原基础功能）
    # ============================================================
    def _build_sim_tab(self, parent):
        frm = ttk.Frame(parent, padding=4)
        frm.pack(fill='both', expand=True)

        def en(row, col, label, default="0", width=10):
            ttk.Label(frm, text=label).grid(column=col, row=row, sticky='w', padx=2, pady=3)
            e = ttk.Entry(frm, width=width)
            e.insert(0, default)
            e.grid(column=col + 1, row=row, padx=2, pady=3)
            return e

        ttk.Label(frm, text="玩家").grid(column=1, row=-1 if False else 0, pady=4)
        ttk.Label(frm, text="电脑").grid(column=3, row=0, pady=4)

        self.s_p_dd = en(1, 0, "玩家DD:", "0", 12)
        self.s_c_dd = en(1, 2, "电脑DD:", "0", 12)
        self.s_p_l  = en(2, 0, "玩家雷电:", "0")
        self.s_c_l  = en(2, 2, "电脑雷电:", "0")
        self.s_p_b  = en(3, 0, "玩家炸药层:", "0")
        self.s_c_b  = en(3, 2, "电脑炸药层:", "0")
        self.s_p_nx = en(4, 0, "玩家聂湘充能:", "0")
        self.s_c_nx = en(4, 2, "电脑聂湘充能:", "0")
        self.s_p_cu = en(5, 0, "玩家云次数:", "0")
        self.s_c_cu = en(5, 2, "电脑云次数:", "0")
        self.s_p_tu = en(6, 0, "玩家田立军次数:", "0")
        self.s_c_tu = en(6, 2, "电脑田立军次数:", "0")
        self.s_p_jy = en(7, 0, "玩家距喦buff(0/1):", "0")
        self.s_c_jy = en(7, 2, "电脑距喦buff(0/1):", "0")
        self.s_p_bu = en(8, 0, "玩家炸药使用次数:", "0")
        self.s_c_bu = en(8, 2, "电脑炸药使用次数:", "0")

        ttk.Button(frm, text="列出玩家合法出招", command=self._sim_list_p).grid(column=0, row=9, pady=6)
        ttk.Button(frm, text="列出电脑合法出招", command=self._sim_list_c).grid(column=1, row=9, pady=6)
        ttk.Button(frm, text="用此状态查询双方GTO", command=self._sim_query_gto).grid(column=2, row=9, pady=6)
        ttk.Button(frm, text="Hard精度选择", command=self._sim_choose_prec).grid(column=3, row=9, pady=6)

        ttk.Label(frm, text="玩家招式:").grid(column=0, row=10, sticky='w')
        self.s_pmove_var = tk.StringVar(value="Charge")
        ttk.Combobox(frm, textvariable=self.s_pmove_var,
                     values=[m.name for m in ALL_MOVES], width=22).grid(column=1, row=10, columnspan=1)
        ttk.Label(frm, text="电脑招式:").grid(column=2, row=10, sticky='w')
        self.s_cmove_var = tk.StringVar(value="Charge")
        ttk.Combobox(frm, textvariable=self.s_cmove_var,
                     values=[m.name for m in ALL_MOVES], width=22).grid(column=3, row=10)

        btns = ttk.Frame(frm)
        btns.grid(column=0, row=11, columnspan=4, pady=8)
        ttk.Button(btns, text="模拟一回合", command=self._sim_run).pack(side='left', padx=4)
        ttk.Button(btns, text="把结果写回为当前输入", command=self._sim_apply).pack(side='left', padx=4)
        ttk.Button(btns, text="重置为默认开局", command=self._sim_reset).pack(side='left', padx=4)

        self.s_out = scrolledtext.ScrolledText(frm, width=88, height=18, wrap='word')
        self.s_out.grid(column=0, row=12, columnspan=4, pady=6, sticky='nsew')
        frm.rowconfigure(12, weight=1)
        for col in range(4):
            frm.columnconfigure(col, weight=1)

        self._last_sim_result = None

    # ============================================================
    # 对战：游戏流程
    # ============================================================
    def _apply_rl_cpu_mode(self):
        if not HAS_RL_AI or self.rl_cpu_mode_var is None:
            return
        mode = self.rl_cpu_mode_var.get()
        self.rl_cpu_mode = mode
        mapping = {"省电": 1, "平衡": 2, "极速": 0}
        n = mapping.get(mode, 2)
        if n <= 0:
            try:
                import multiprocessing as _mp
                n = min(8, max(1, _mp.cpu_count() or 4))
            except Exception:
                n = 4
        try:
            set_rl_inference_threads(n)
        except Exception:
            pass
        if self.game_active:
            self._log(f"[RL] CPU模式切换为: {mode} (threads={n})")

    # ============================================================
    # BO（Best of N）赛制 辅助函数
    # ============================================================
    def _on_bo_changed(self):
        """用户切换了赛制下拉框"""
        label = self.bo_var.get()
        n = self._bo_label_map.get(label, 1)
        if n == -1:
            # 自定义 N → 弹输入框
            self._ask_custom_bo_n()
            return
        # BO 已经开始了（比分>0 或 match_active=True）→ 先问是否清零，用户同意才改
        if (self.bo_match_active or self.bo_player_wins + self.bo_cpu_wins > 0) and n != self.bo_n:
            if not messagebox.askyesno(
                "确认切换赛制",
                f"当前 BO{self.bo_n} 已开始（你 {self.bo_player_wins}:{self.bo_cpu_wins} 电脑）\n"
                f"切换到 {label} 会清零比分并重置 BO，确定要切吗？",
            ):
                # 取消：把下拉值滚回当前 bo_n
                self.bo_var.set(self._bo_label_inv.get(self.bo_n, "单局（BO1）"))
                return
            self._reset_bo_match(silent=True)
        self.bo_n = n
        self.bo_win_target = n // 2 + 1
        # 下方 tooltip 更新
        if n == 1:
            tip = "单局：一局定胜负，打完这局就结束"
        elif n <= 5:
            tip = f"短盘 BO{n}：先赢 {self.bo_win_target} 小局者胜，适合热身对练"
        elif n <= 11:
            tip = f"中盘 BO{n}：先赢 {self.bo_win_target} 小局者胜，接近正式切磋"
        else:
            tip = f"长盘 BO{n}：先赢 {self.bo_win_target} 小局者胜，适合分高低/定排名"
        try:
            self._bo_help_lbl.config(text=tip)
        except Exception:
            pass
        self._update_bo_score_ui()

    def _ask_custom_bo_n(self):
        """自定义 BO N 弹 Entry 窗口，要求奇数>=1，默认 7"""
        win = tk.Toplevel(self.root); win.title("自定义 BO 赛制 N")
        win.transient(self.root); win.geometry("320x160")
        f = ttk.Frame(win, padding=10); f.pack(fill='both', expand=True)
        ttk.Label(f, text="请输入 BO N（必须是正奇数，如 3/5/7/9/21/31）：",
                  wraplength=280, justify='left').pack(anchor='w')
        ev = tk.StringVar(value="7")
        e = ttk.Entry(f, textvariable=ev, width=14, font=("Segoe UI", 11))
        e.pack(anchor='w', pady=8); e.focus_set()
        hint = ttk.Label(f, text="", foreground="#b00", wraplength=280, justify='left')
        hint.pack(anchor='w')

        def ok():
            s = ev.get().strip()
            if not s.lstrip('-').isdigit():
                hint.config(text="❌ 请输入正整数")
                return
            x = int(s)
            if x < 1:
                hint.config(text="❌ N 必须 >= 1")
                return
            if x % 2 == 0:
                hint.config(text="❌ N 必须是奇数（避免 55 开，总有一方先到胜场）")
                return
            # 用户同意改 N（且会清比分）
            if (self.bo_match_active or self.bo_player_wins + self.bo_cpu_wins > 0) and x != self.bo_n:
                if not messagebox.askyesno(
                    "确认自定义 N",
                    f"当前 BO{self.bo_n} 已开始（你 {self.bo_player_wins}:{self.bo_cpu_wins} 电脑）\n"
                    f"改成 BO{x} 会清零比分并重置 BO，确定吗？",
                ):
                    # 用户取消，把下拉回滚到旧 bo_n
                    self.bo_var.set(self._bo_label_inv.get(self.bo_n, "单局（BO1）"))
                    win.destroy(); return
                self._reset_bo_match(silent=True)
            self.bo_n = x
            self.bo_win_target = x // 2 + 1
            tip = f"自定义 BO{x}：先赢 {self.bo_win_target} 小局者胜"
            try:
                self._bo_help_lbl.config(text=tip)
            except Exception:
                pass
            # 下拉选中保持在「自定义 N…」
            self._update_bo_score_ui()
            win.destroy()

        ttk.Button(f, text="确定", command=ok).pack(side='right', padx=4)
        def cancel():
            # 取消：滚回旧 bo_n
            self.bo_var.set(self._bo_label_inv.get(self.bo_n, "单局（BO1）"))
            win.destroy()
        ttk.Button(f, text="取消", command=cancel).pack(side='right')
        win.bind("<Return>", lambda _e: ok())
        win.bind("<Escape>", lambda _e: cancel())

    def _reset_bo_match(self, silent=False):
        """用户点「重置本次BO」或切换赛制时被调用，清比分但不改 difficulty / precision"""
        self.bo_player_wins = 0
        self.bo_cpu_wins = 0
        self.bo_current_game = 0
        self.bo_match_active = False
        self.game_active = False
        self._update_bo_score_ui()
        self._refresh_start_btn_text()
        if not silent:
            self._log(f"\n【BO 已重置】比分清零，BO{self.bo_n} 重新开始。\n\n")
            # 如果对局记录面板上还有当前已结束的小局，给个提示
            try:
                self.status_lbl.config(
                    text=f"BO{self.bo_n} 已重置（比分 0:0），点「开始新 BO」打第 1 小局。\n")
            except Exception:
                pass

    def _update_bo_score_ui(self):
        """BO 比分面板实时刷新：文本 + 显示/隐藏"""
        if self.bo_n <= 1:
            # BO1 不需要比分面板
            try:
                self._bo_score_frm.pack_forget()
            except Exception:
                pass
            return
        # BO>=3：显示面板 + 更新文本
        try:
            self._bo_score_frm.pack(fill='x', before=self.status_frm, pady=(0, 6))
        except Exception:
            pass
        # 文本
        you = self.bo_player_wins; cpu = self.bo_cpu_wins
        need = self.bo_win_target
        you_left = max(need - you, 0); cpu_left = max(need - cpu, 0)
        if you > cpu:
            color = "#070"  # 绿=你领先
            lead_txt = f"你领先，还差 {you_left} 局拿下 BO{self.bo_n}"
        elif cpu > you:
            color = "#a00"  # 红=电脑领先
            lead_txt = f"电脑领先，你还差 {you_left} 局，电脑差 {cpu_left} 局"
        else:
            color = "#000"  # 黑=平
            lead_txt = f"比分打平，双方都还差 {need} 局赢 BO{self.bo_n}"
        if self.bo_match_active:
            game_txt = f"小局进度：第 {self.bo_current_game} 小局进行中"
        elif you + cpu == 0:
            game_txt = "未开始（点「开始新 BO」打第 1 小局）"
        else:
            game_txt = f"上一小局：第 {self.bo_current_game} 小局已结束，点「开始下一小局」继续"
        text = (f"BO{self.bo_n}（先赢 {self.bo_win_target} 小局获胜）   "
                f"你 {you} : {cpu} 电脑   |   {game_txt}\n"
                f"赛况：{lead_txt}")
        try:
            self._bo_score_lbl.config(text=text, foreground=color)
        except Exception:
            pass

    def _refresh_start_btn_text(self):
        """根据 BO 状态动态改「开始」按钮的文字，新手一看就知道点了干嘛"""
        if self.bo_n <= 1:
            # BO1：永远「开始新对局」
            try:
                self._bo_start_btn.config(text=self._bo_start_btn_text_default)
            except Exception:
                pass
            return
        you = self.bo_player_wins; cpu = self.bo_cpu_wins
        if (not self.bo_match_active) and you == 0 and cpu == 0:
            txt = f"开始新 BO{self.bo_n}（先赢 {self.bo_win_target} 局）"
        elif self.game_active:
            txt = "本局进行中…"
        elif max(you, cpu) >= self.bo_win_target:
            txt = f"BO{self.bo_n} 已结束，开新 BO"
        else:
            txt = f"开始第 {self.bo_current_game + 1} 小局（当前 {you}:{cpu}）"
        try:
            self._bo_start_btn.config(text=txt)
        except Exception:
            pass

    def start_new_game(self):
        # 先读赛制（用户可能还没点过下拉就点开始）
        try:
            label = self.bo_var.get()
            n = self._bo_label_map.get(label, 1)
            if n != -1:
                self.bo_n = n
                self.bo_win_target = n // 2 + 1
        except Exception:
            pass
        self.difficulty = self.diff_var.get()
        self.precision = self.prec_var.get()
        if self.rl_cpu_mode_var is not None:
            self._apply_rl_cpu_mode()
        self.gto = make_gto_solver(self.precision)
        self.round_no = 1
        self.player = PlayerState()
        self.cpu = PlayerState()
        self.game_active = True

        # ===== BO 逻辑分支 =====
        you_old = self.bo_player_wins; cpu_old = self.bo_cpu_wins
        bo_over = (max(you_old, cpu_old) >= self.bo_win_target)
        if self.bo_n > 1:
            if bo_over or (you_old == 0 and cpu_old == 0 and not self.bo_match_active):
                # 要么 BO 已结束重新开，要么还没开始（0:0）点「开始新 BO」→ 都从第1局重新计数
                self.bo_player_wins = 0
                self.bo_cpu_wins = 0
                self.bo_current_game = 1
                self.bo_match_active = True
                self.log.delete('1.0', 'end')  # 新 BO 才清空整份 log
            else:
                # BO 进行中→这是下一小局，不清 log，保留历史记录
                self.bo_current_game += 1
                self.bo_match_active = True
        else:
            # BO1：行为跟老版完全一致，log 清空
            self.bo_match_active = True
            self.bo_player_wins = 0
            self.bo_cpu_wins = 0
            self.bo_current_game = 1
            self.log.delete('1.0', 'end')

        self._first_query_help_shown = False
        dlabel = DIFFICULTY_LABEL.get(self.difficulty, self.difficulty)
        # BO 模式下 log 多写一行小局编号
        if self.bo_n > 1:
            self._log(f"【BO{self.bo_n} 第 {self.bo_current_game} 小局开始】 "
                      f"当前比分：你 {self.bo_player_wins} : {self.bo_cpu_wins} 电脑\n")
            self._log(f"       AI难度={dlabel}\n")
        else:
            self._log(f"【新对局】{dlabel}\n")
        self._log(f"       普通AI精度={self.precision}（{PRECISION_HINT.get(self.precision,'')}）\n")
        if self.difficulty == "Hard":
            self._log("       每回合电脑按「近似GTO无剥削混合策略」出招，你按 GTO 提示的概率混合出招，长期不会输。\n")
        elif self.difficulty == "RL Hard":
            if rl_model_available():
                self._log("       电脑用「PPO 自对战 853 万步训练」的策略 + 专家规则出招，最接近人类顶级玩家。\n")
            else:
                self._log("       ⚠️ 未检测到 rl_checkpoints\\latest.zip，暂时退回简单 AI。请把 latest.zip 放到 rl_checkpoints 目录下。\n")
        else:
            self._log("       启发式出招，有大量随机性，适合新手练手/熟悉招式。\n")
        self._log("提示：招式按钮「右键」= 看这招的作用/相克/新手坑提示；左上角「完整规则手册」= 总规则表。\n\n")
        self._update_bo_score_ui()
        self._refresh_start_btn_text()
        self._update_status_and_moves()

    def _on_diff_changed(self):
        k = self.diff_var.get()
        try:
            self.status_lbl.config(text=DIFFICULTY_HINT_SHORT.get(k, ""))
        except Exception:
            pass

    def _on_prec_changed(self):
        k = self.prec_var.get()
        try:
            self._prec_label.config(text=PRECISION_HINT.get(k, ""))
        except Exception:
            pass

    def show_move_single_info(self, m: Move):
        txt = _format_move_details(m)
        title = MOVE_NAMES_CN.get(m, m.name)
        win = tk.Toplevel(self.root)
        win.title(f"招式说明：{title}")
        win.geometry("520x380")
        tx = scrolledtext.ScrolledText(win, wrap='word', font=("Segoe UI", 10))
        tx.pack(fill='both', expand=True, padx=8, pady=8)
        tx.insert('1.0', txt)
        tx.config(state='disabled')

    def _state_line(self, p: PlayerState, c: PlayerState) -> str:
        def line(name, s: PlayerState):
            extras = []
            if s.juyanBuff: extras.append("距喦buff")
            if s.hasHighAttackRecord:
                extras.append(f"ZXW记录:{MOVE_NAMES_CN.get(s.lastHighAttack, s.lastHighAttack.name)}")
            if s.zhangUsed: extras.append("ZXW已用")
            if s.liqUsed: extras.append("历强已用")
            bp = ','.join(str(x) for x in s.bombPending)
            extra = f"  [{'; '.join(extras)}]" if extras else ""
            return (f"{name}: DD={format_dd_units(s.dd)}  雷电={s.lightning}  "
                    f"炸药层={s.bombLayers}(延迟:{bp})  聂湘充能={s.nxCharge}  "
                    f"云次数={s.cloudUses}  田立军次数={s.tianUses}{extra}")
        return line("你", p) + "\n" + line("电脑", c)

    def _update_status_and_moves(self):
        self.status_lbl.config(
            text=f"回合 {self.round_no}\n" + self._state_line(self.player, self.cpu))
        self._refresh_move_buttons()

    def _refresh_move_buttons(self):
        for w in self.move_btns_frame.winfo_children():
            w.destroy()
        if not self.game_active:
            if self.bo_n > 1:
                you = self.bo_player_wins; cpu = self.bo_cpu_wins
                over = max(you, cpu) >= self.bo_win_target
                if over:
                    winner = "你" if you > cpu else "电脑"
                    ttk.Label(self.move_btns_frame,
                              text=(f"（BO{self.bo_n} 已结束：{winner} {max(you,cpu)}:{min(you,cpu)} 获胜！\n"
                                    f"   点右上角「开始新 BO」再来一场）")).pack(pady=10)
                else:
                    ttk.Label(self.move_btns_frame,
                              text=(f"（当前 BO{self.bo_n} 比分 你 {you}:{cpu} 电脑，\n"
                                    f"   点上方「开始第 {self.bo_current_game + 1} 小局」）")).pack(pady=10)
            else:
                ttk.Label(self.move_btns_frame,
                          text="（请先点“开始新对局”）").pack()
            return
        legal = list_legal_moves(self.player, self.cpu)
        if not legal:
            ttk.Label(self.move_btns_frame, text="（你当前无合法招式？）").pack()
            return
        cols = 3
        for idx, m in enumerate(legal):
            r = idx // cols
            co = idx % cols
            cost = dd_cost_units_for_move(self.player, m)
            label = move_label(m, self.player)
            btn = ttk.Button(self.move_btns_frame,
                             text=f"{label}\nDD={format_dd_units(cost)}",
                             command=lambda mv=m: self.play_move(mv))
            btn.grid(row=r, column=co, sticky='nsew', padx=2, pady=2)
            btn.bind("<Button-3>", lambda e, mv=m: self.show_move_single_info(mv))
            btn.bind("<Button-2>", lambda e, mv=m: self.show_move_single_info(mv))
        for c in range(cols):
            self.move_btns_frame.columnconfigure(c, weight=1)

    def play_move(self, pmove: Move):
        if not self.game_active:
            messagebox.showinfo("提示", "请先点「开始新对局」。"); return
        legal = list_legal_moves(self.player, self.cpu)
        if pmove not in legal:
            messagebox.showerror("错误", f"{pmove.name} 当前不合法"); return

        if self.difficulty == "Hard":
            cmove = self.gto.choose_move_for_cpu(self.player, self.cpu, self.rng)
        elif self.difficulty == "RL Hard":
            cmove = choose_rl_move(self.cpu, self.player, self.rng, fallback_easy=True)
        else:
            cmove = choose_easy_move(self.cpu, self.player, self.rng)
        # double-check legality for cpu
        cpu_legal = list_legal_moves(self.cpu, self.player)
        if cmove not in cpu_legal:
            cmove = self.rng.choice(cpu_legal) if cpu_legal else Move.Charge

        self._log(f"—— 回合 {self.round_no} ——\n")
        pdesc = MOVE_NAMES_CN.get(pmove, pmove.name)
        if pmove == Move.ZhangXinWei and self.player.hasHighAttackRecord:
            pdesc += f"(→{MOVE_NAMES_CN.get(self.player.lastHighAttack, self.player.lastHighAttack.name)})"
        cdesc = MOVE_NAMES_CN.get(cmove, cmove.name)
        if cmove == Move.ZhangXinWei and self.cpu.hasHighAttackRecord:
            cdesc += f"(→{MOVE_NAMES_CN.get(self.cpu.lastHighAttack, self.cpu.lastHighAttack.name)})"
        self._log(f"你出：{pdesc}  [DD={format_dd_units(dd_cost_units_for_move(self.player, pmove))}]\n")
        self._log(f"电脑出：{cdesc}  [DD={format_dd_units(dd_cost_units_for_move(self.cpu, cmove))}]\n")

        tr = simulate_turn(self.player, self.cpu, pmove, cmove)
        self.player = tr.nextP
        self.cpu = tr.nextC

        if tr.outcome == Outcome.Continue:
            self._log("结果：继续下一回合。\n\n")
            self.round_no += 1
            self._update_status_and_moves()
            return
        # ========== 小局结束 ==========
        player_won_game = (tr.outcome == Outcome.PlayerWin)
        cpu_won_game = (tr.outcome == Outcome.CpuWin)
        if player_won_game:
            self._log("🏆 结果：你赢了这一小局！\n")
        elif cpu_won_game:
            self._log("🤖 结果：电脑赢了这一小局。\n")
        else:
            self._log("🤝 结果：平局（双方同时自杀），不计入 BO 比分。\n")
        self._log(f"最终：\n{self._state_line(self.player, self.cpu)}\n\n")
        self.game_active = False

        # ========== BO 赛制累计比分 + 判胜负 ==========
        bo_finished = False
        if self.bo_n > 1 and (player_won_game or cpu_won_game):
            if player_won_game:
                self.bo_player_wins += 1
            else:
                self.bo_cpu_wins += 1
            you = self.bo_player_wins; cpu = self.bo_cpu_wins
            need = self.bo_win_target
            # 判 BO 是否结束（有人到达 win_target）
            if you >= need or cpu >= need:
                bo_finished = True
                self.bo_match_active = False
                if you > cpu:
                    w = "你"
                    icon = "🏆🏆🏆"
                    color = "#070"
                else:
                    w = "电脑"
                    icon = "🤖🤖🤖"
                    color = "#a00"
                self._log(
                    f"\n{icon} 【BO{self.bo_n} 整场结束】{w}获胜！\n"
                    f"     最终比分：你 {you} : {cpu} 电脑\n"
                    f"     （先赢 {need} 小局者胜，共打了 {self.bo_current_game} 小局）\n\n"
                )
                msg = (f"{icon}\nBO{self.bo_n} 整场结束！\n\n"
                       f"胜者：{w}\n"
                       f"最终比分：你 {you}  :  {cpu} 电脑\n"
                       f"共进行了 {self.bo_current_game} 小局")
                # 弹结果框（用 messagebox.showinfo 在 GUI 线程里）
                try:
                    messagebox.showinfo(f"BO{self.bo_n} 结果：{w}获胜！", msg)
                except Exception:
                    pass
            else:
                # BO 还没结束：log 当前比分 + 还差几局
                you_left = need - you; cpu_left = need - cpu
                self._log(
                    f"【BO{self.bo_n} 当前比分】你 {you} : {cpu} 电脑\n"
                    f"     你还差 {you_left} 局拿下 BO，电脑差 {cpu_left} 局。\n"
                    f"     点上方「开始第 {self.bo_current_game + 1} 小局」继续～\n\n"
                )

        # UI 更新
        self._update_bo_score_ui()
        self._refresh_start_btn_text()
        self._update_status_and_moves()
        if bo_finished:
            self.status_lbl.config(
                text=(f"🎉 BO{self.bo_n} 已结束！你 {self.bo_player_wins}:{self.bo_cpu_wins} 电脑，"
                      + ("你获胜！" if self.bo_player_wins > self.bo_cpu_wins else "电脑获胜。")
                      + f"\n点上方「开新 BO」再战？\n")
            )
        elif self.bo_n > 1:
            self.status_lbl.config(
                text=(f"BO{self.bo_n} 第 {self.bo_current_game} 小局已结束，"
                      f"比分 你 {self.bo_player_wins}:{self.bo_cpu_wins} 电脑。\n"
                      f"点上方「开始第 {self.bo_current_game + 1} 小局」继续。\n")
            )
        else:
            # BO1：老版提示
            self.status_lbl.config(text="对局已结束，请点「开始新对局」再来一局。\n"
                                        + self.status_lbl.cget("text"))

    # ============================================================
    # GTO 助手
    # ============================================================
    def show_gto_current(self):
        if not self.game_active:
            messagebox.showinfo("提示", "请先开始对局，或用下方按钮查询任意状态。")
            return
        self._busy(True)
        self.root.update_idletasks()
        try:
            cfg = PRECISION_PROFILES[self.precision]
            self._log(f"[GTO] 正在求解近似GTO（迭代={cfg['iter']}，γ={cfg['gamma']}）…\n")
            self.root.update_idletasks()
            p_legal, c_legal, p_probs, c_probs, value = self.gto.solve(self.player, self.cpu)
            self._render_gto_result(self.player, self.cpu, p_legal, c_legal, p_probs, c_probs, value,
                                    title="当前局面的近似GTO")
        finally:
            self._busy(False)

    def query_gto_state(self):
        if not self._first_query_help_shown:
            self._first_query_help_shown = True
            messagebox.showinfo(
                "任意状态GTO查询",
                "下一步会弹出输入框，让你填玩家与电脑的各资源值。\n"
                "DD 支持：整数、1/3、2+1/2 等。\n"
                "其他值填非负整数即可。\n"
                "若某些值留空，则默认视为 0。")
        self._open_query_dialog(self.player, self.cpu, callback=None)

    def _open_query_dialog(self, default_p: PlayerState, default_c: PlayerState, callback):
        dlg = tk.Toplevel(self.root)
        dlg.title("输入状态查询 GTO")
        dlg.transient(self.root)
        frm = ttk.Frame(dlg, padding=10); frm.pack(fill='both', expand=True)

        def add_field(r, label, default_val, is_dd=False):
            ttk.Label(frm, text=label).grid(column=0, row=r, sticky='w', padx=2, pady=2)
            e = ttk.Entry(frm, width=16)
            e.insert(0, default_val)
            e.grid(column=1, row=r, padx=2, pady=2)
            return e

        rows = []
        def mkrow(i, key, p_default, c_default, is_dd=False):
            ttk.Label(frm, text=key).grid(column=0, row=i, sticky='e')
            pe = add_field(i, "玩家", p_default, is_dd)
            ce = add_field(i, "电脑", c_default, is_dd)
            rows.append((key, pe, ce, is_dd))

        ttk.Label(frm, text="字段").grid(column=0, row=0)
        ttk.Label(frm, text="玩家").grid(column=1, row=0)
        ttk.Label(frm, text="电脑").grid(column=2, row=0)

        i = 1
        mkrow(i, "DD", format_dd_units(default_p.dd), format_dd_units(default_c.dd), True); i += 1
        mkrow(i, "雷电", str(default_p.lightning), str(default_c.lightning)); i += 1
        mkrow(i, "炸药层", str(default_p.bombLayers), str(default_c.bombLayers)); i += 1
        mkrow(i, "炸药使用次数", str(default_p.bombUses), str(default_c.bombUses)); i += 1
        mkrow(i, "炸药延迟(0,0,0)", ','.join(map(str, default_p.bombPending)),
              ','.join(map(str, default_c.bombPending))); i += 1
        mkrow(i, "聂湘充能", str(default_p.nxCharge), str(default_c.nxCharge)); i += 1
        mkrow(i, "云次数", str(default_p.cloudUses), str(default_c.cloudUses)); i += 1
        mkrow(i, "田立军次数", str(default_p.tianUses), str(default_c.tianUses)); i += 1
        mkrow(i, "距喦buff(0/1)", "1" if default_p.juyanBuff else "0",
              "1" if default_c.juyanBuff else "0"); i += 1
        mkrow(i, "ZXW已用(0/1)", "1" if default_p.zhangUsed else "0",
              "1" if default_c.zhangUsed else "0"); i += 1
        mkrow(i, "历强已用(0/1)", "1" if default_p.liqUsed else "0",
              "1" if default_c.liqUsed else "0"); i += 1
        mkrow(i, "ZXW有记录(0/1)", "1" if default_p.hasHighAttackRecord else "0",
              "1" if default_c.hasHighAttackRecord else "0"); i += 1

        ttk.Label(frm, text="（以下填招式名，ZXW记录/上一招；留空=按默认）").grid(
            column=0, row=i, columnspan=3, sticky='w', pady=(6, 2)); i += 1
        ttk.Label(frm, text="ZXW记录招式(p.ha/c.ha)").grid(column=0, row=i, sticky='e')
        ha_p = ttk.Entry(frm, width=16); ha_p.grid(column=1, row=i)
        ha_c = ttk.Entry(frm, width=16); ha_c.grid(column=2, row=i)
        if default_p.hasHighAttackRecord:
            ha_p.insert(0, default_p.lastHighAttack.name)
        if default_c.hasHighAttackRecord:
            ha_c.insert(0, default_c.lastHighAttack.name)
        i += 1
        ttk.Label(frm, text="上一招(p.last/c.last)").grid(column=0, row=i, sticky='e')
        lst_p = ttk.Entry(frm, width=16); lst_p.grid(column=1, row=i)
        lst_c = ttk.Entry(frm, width=16); lst_c.grid(column=2, row=i)
        lst_p.insert(0, default_p.lastMove.name)
        lst_c.insert(0, default_c.lastMove.name)

        def run_query():
            try:
                p = PlayerState(); c = PlayerState()
                # build reverse move name lookup
                move_by_name = {m.name: m for m in ALL_MOVES}
                for (key, pe, ce, is_dd) in rows:
                    pv = pe.get().strip(); cv = ce.get().strip()
                    if is_dd:
                        p.dd = parse_dd_units(pv or "0")
                        c.dd = parse_dd_units(cv or "0")
                    elif key == "炸药延迟(0,0,0)":
                        p.bombPending = self._parse_bp(pv)
                        c.bombPending = self._parse_bp(cv)
                    else:
                        def to_boolish(v):
                            if v == "": return 0
                            if v.lower() in {"true", "yes", "y"}: return 1
                            if v.lower() in {"false", "no", "n"}: return 0
                            return int(v)
                        if key in {"距喦buff(0/1)","ZXW已用(0/1)","历强已用(0/1)","ZXW有记录(0/1)"}:
                            pv_i = bool(to_boolish(pv)); cv_i = bool(to_boolish(cv))
                        else:
                            pv_i = int(pv or "0"); cv_i = int(cv or "0")
                        self._assign_state_field(p, key, pv_i, True)
                        self._assign_state_field(c, key, cv_i, False)
                # handle ha / last via move names
                def to_move(s: str, default: Move) -> Move:
                    s = s.strip()
                    if not s: return default
                    if s in move_by_name: return move_by_name[s]
                    # try CN match
                    for m, cn in MOVE_NAMES_CN.items():
                        if cn == s or s in cn:
                            return m
                    raise ValueError(f"未知招式名: {s}")
                p.hasHighAttackRecord = bool(p.hasHighAttackRecord)
                c.hasHighAttackRecord = bool(c.hasHighAttackRecord)
                if p.hasHighAttackRecord:
                    p.lastHighAttack = to_move(ha_p.get(), default_p.lastHighAttack)
                if c.hasHighAttackRecord:
                    c.lastHighAttack = to_move(ha_c.get(), default_c.lastHighAttack)
                p.lastMove = to_move(lst_p.get(), default_p.lastMove)
                c.lastMove = to_move(lst_c.get(), default_c.lastMove)
            except Exception as e:
                messagebox.showerror("输入错误", f"解析失败: {e}"); return

            self._busy(True); self.root.update_idletasks()
            try:
                cfg = PRECISION_PROFILES[self.precision]
                self._log(f"[GTO查询] 迭代={cfg['iter']}，γ={cfg['gamma']}，正在求解…\n")
                self.root.update_idletasks()
                p_l, c_l, p_p, c_p, value = self.gto.solve(p, c)
                self._render_gto_result(p, c, p_l, c_l, p_p, c_p, value,
                                        title="查询状态的近似GTO")
            finally:
                self._busy(False)
            if callback:
                try: callback(p, c, p_l, c_l, p_p, c_p, value)
                except Exception: pass
            dlg.destroy()

        ttk.Button(frm, text="开始求解近似GTO", command=run_query).grid(
            column=0, row=i + 1, columnspan=3, pady=(12, 0))

    def _parse_bp(self, s: str):
        s = s.strip() or "0,0,0"
        parts = s.split(',')
        if len(parts) != 3:
            raise ValueError("炸药延迟需要 3 个逗号分隔数（如 0,1,0）")
        vals = [int(x.strip() or "0") for x in parts]
        return [max(0, v) for v in vals]

    def _assign_state_field(self, s: PlayerState, key: str, val, is_player: bool):
        mapping = {
            "雷电": "lightning",
            "炸药层": "bombLayers",
            "炸药使用次数": "bombUses",
            "聂湘充能": "nxCharge",
            "云次数": "cloudUses",
            "田立军次数": "tianUses",
            "距喦buff(0/1)": "juyanBuff",
            "ZXW已用(0/1)": "zhangUsed",
            "历强已用(0/1)": "liqUsed",
            "ZXW有记录(0/1)": "hasHighAttackRecord",
        }
        attr = mapping.get(key)
        if attr is None:
            return
        setattr(s, attr, val)

    def _render_gto_result(self, p, c, p_l, c_l, p_p, c_p, value, title):
        wr = value_to_reference_winrate(value) * 100.0
        def line(name, moves, probs):
            items = []
            shown = 0
            for m, pr in zip(moves, probs):
                if pr > 1e-5:
                    items.append((MOVE_NAMES_CN.get(m, m.name), pr * 100.0))
                    shown += 1
            items.sort(key=lambda t: -t[1])
            hidden = len(moves) - shown
            lines = [f"  [本回合共考虑 {len(moves)} 个合法招式]"]
            lines += [f"  - {n}: {pct:.3f}%" for n, pct in items]
            if hidden > 0:
                lines.append(f" （另有 {hidden} 个招式概率 < 0.001%，未逐行列出）")
            return "\n".join(lines)

        def list_all_names(moves):
            return "、".join([MOVE_NAMES_CN.get(m, m.name) for m in moves])

        self._log(f"\n===== {title} =====\n")
        self._log(f"状态：\n{self._state_line(p, c)}\n")
        self._log(f"玩家合法招式列表（全部已纳入策略计算）：\n  {list_all_names(p_l)}\n")
        self._log(f"玩家（你）策略：\n{line('P', p_l, p_p)}\n")
        self._log(f"电脑合法招式列表（全部已纳入策略计算）：\n  {list_all_names(c_l)}\n")
        self._log(f"电脑策略：\n{line('C', c_l, c_p)}\n")
        self._log(f"该局面对玩家估值 V≈{value:+.4f}  参考胜率≈{wr:.2f}%\n"
                  f"（参考胜率：把 V∈[-1,1] 映射到 0~100% 直观值；未列出的招式是近似概率≈0）\n")
        self._log("===== 结束 =====\n\n")

    # ============================================================
    # 模拟模式功能
    # ============================================================
    def _sim_collect_state(self):
        try:
            p = PlayerState()
            c = PlayerState()
            p.dd = parse_dd_units(self.s_p_dd.get())
            c.dd = parse_dd_units(self.s_c_dd.get())
            def ival(ctrl, default=0):
                try:
                    s = ctrl.get().strip()
                    if s == "": return default
                    return int(s)
                except Exception:
                    raise ValueError("请输入整数")
            def bval(ctrl):
                s = ctrl.get().strip().lower()
                if s == "" or s in {"0", "false", "no", "n"}: return False
                if s in {"1", "true", "yes", "y"}: return True
                raise ValueError("布尔值请填 0/1")
            p.lightning = ival(self.s_p_l); c.lightning = ival(self.s_c_l)
            p.bombLayers = ival(self.s_p_b); c.bombLayers = ival(self.s_c_b)
            p.nxCharge = ival(self.s_p_nx); c.nxCharge = ival(self.s_c_nx)
            p.cloudUses = ival(self.s_p_cu); c.cloudUses = ival(self.s_c_cu)
            p.tianUses = ival(self.s_p_tu); c.tianUses = ival(self.s_c_tu)
            p.juyanBuff = bval(self.s_p_jy); c.juyanBuff = bval(self.s_c_jy)
            p.bombUses = ival(self.s_p_bu); c.bombUses = ival(self.s_c_bu)
            return p, c
        except Exception as e:
            messagebox.showerror("输入错误", str(e)); raise

    def _sim_list_p(self):
        try: p, c = self._sim_collect_state()
        except: return
        moves = list_legal_moves(p, c)
        lines = [f"玩家合法招式（{len(moves)} 个）："]
        for m in moves:
            t = MOVE_DETAILS_CN.get(m)
            if t:
                title, cost, _ = t
                lines.append(f"  - {MOVE_NAMES_CN.get(m, m.name)}  [成本 {cost}]  → 双击/右键可看完整说明")
            else:
                lines.append(f"  - {MOVE_NAMES_CN.get(m, m.name)}")
        lines.append("（右键看招式详细说明，左键列出是看列表。）\n\n")
        self.s_out.insert('end', "\n".join(lines))
        self.s_out.see('end')

    def _sim_list_c(self):
        try: p, c = self._sim_collect_state()
        except: return
        moves = list_legal_moves(c, p)
        lines = [f"电脑合法招式（{len(moves)} 个）："]
        for m in moves:
            t = MOVE_DETAILS_CN.get(m)
            if t:
                title, cost, _ = t
                lines.append(f"  - {MOVE_NAMES_CN.get(m, m.name)}  [成本 {cost}]")
            else:
                lines.append(f"  - {MOVE_NAMES_CN.get(m, m.name)}")
        lines.append("\n")
        self.s_out.insert('end', "\n".join(lines))
        self.s_out.see('end')

    def _sim_choose_prec(self):
        win = tk.Toplevel(self.root); win.title("普通AI精度（GTO 迭代次数）")
        win.transient(self.root); ttk.Frame(win, padding=10).pack()
        frm = win.winfo_children()[0]
        ttk.Label(frm, text="精度:").grid(row=0, column=0)
        v = tk.StringVar(value=self.prec_var.get())
        cb = ttk.Combobox(frm, textvariable=v, values=list(PRECISION_PROFILES.keys()),
                          state='readonly', width=8)
        cb.grid(row=0, column=1, padx=4)
        hint_lbl = ttk.Label(frm, text=PRECISION_HINT.get(v.get(), ""), foreground="#555",
                             wraplength=320, justify='left')
        hint_lbl.grid(row=1, column=0, columnspan=3, sticky='w', pady=(4, 0))
        def _on_cb(_ev=None):
            hint_lbl.config(text=PRECISION_HINT.get(v.get(), ""))
        cb.bind("<<ComboboxSelected>>", _on_cb)
        def save():
            self.prec_var.set(v.get())
            self.precision = v.get()
            self.gto = make_gto_solver(self.precision)
            self.s_out.insert('end', f"[设置] 普通AI精度已切为：{v.get()}（{PRECISION_HINT.get(v.get(),'')}）\n\n")
            win.destroy()
        ttk.Button(frm, text="确定", command=save).grid(row=0, column=2, padx=6)

    def _sim_query_gto(self):
        try: p, c = self._sim_collect_state()
        except: return
        self.s_out.insert('end', f"[GTO查询] 求解中（{self.precision}）…\n")
        self.s_out.update_idletasks()
        p_l, c_l, p_p, c_p, value = self.gto.solve(p, c)
        wr = value_to_reference_winrate(value) * 100.0
        def fmt(label, moves, probs):
            items = []
            shown = 0
            for m, pr in zip(moves, probs):
                if pr > 1e-5:
                    items.append((MOVE_NAMES_CN.get(m, m.name), 100.0 * pr))
                    shown += 1
            items.sort(key=lambda t: -t[1])
            hidden = len(moves) - shown
            lines = [f"{label}合法招式（共 {len(moves)} 个，全部已纳入计算）："]
            lines.append("  " + "、".join([MOVE_NAMES_CN.get(m, m.name) for m in moves]))
            lines.append(f"{label}策略：")
            lines += [f"  - {n}: {pct:.3f}%" for n, pct in items]
            if hidden > 0:
                lines.append(f" （另有 {hidden} 个招式概率 < 0.001%，未逐行列出）")
            return "\n".join(lines)
        self.s_out.insert('end',
            (f"===== 查询状态近似GTO =====\n"
             f"玩家DD={format_dd_units(p.dd)} 雷电={p.lightning} 炸药层={p.bombLayers} "
             f"聂湘充能={p.nxCharge}\n"
             f"电脑DD={format_dd_units(c.dd)} 雷电={c.lightning} 炸药层={c.bombLayers} "
             f"聂湘充能={c.nxCharge}\n"
             f"{fmt('玩家', p_l, p_p)}\n"
             f"{fmt('电脑', c_l, c_p)}\n"
             f"玩家估值V≈{value:+.4f}  参考胜率≈{wr:.2f}%\n"
             f"（未列出的招式：近似概率≈0）\n"
             f"==========================\n\n"))
        self.s_out.see('end')

    def _sim_run(self):
        try: p, c = self._sim_collect_state()
        except: return
        try:
            pm = Move[self.s_pmove_var.get().strip()]
            cm = Move[self.s_cmove_var.get().strip()]
        except Exception as e:
            messagebox.showerror("输入错误", f"未知招式: {e}"); return
        if pm not in list_legal_moves(p, c):
            self.s_out.insert('end', "[警告] 玩家招式当前不合法\n")
        if cm not in list_legal_moves(c, p):
            self.s_out.insert('end', "[警告] 电脑招式当前不合法\n")
        tr = simulate_turn(p, c, pm, cm)
        self._last_sim_result = tr
        out = (f"—— 模拟回合 ——\n"
               f"玩家: {MOVE_NAMES_CN.get(pm, pm.name)}  电脑: {MOVE_NAMES_CN.get(cm, cm.name)}\n"
               f"结果: {tr.outcome.name}\n"
               f"玩家净DD变化(吸收/云)单位: {tr.ddGainP}  电脑: {tr.ddGainC}\n"
               f"下回合 玩家 DD={format_dd_units(tr.nextP.dd)} 雷电={tr.nextP.lightning} "
               f"炸药层={tr.nextP.bombLayers} 聂湘充能={tr.nextP.nxCharge}\n"
               f"下回合 电脑 DD={format_dd_units(tr.nextC.dd)} 雷电={tr.nextC.lightning} "
               f"炸药层={tr.nextC.bombLayers} 聂湘充能={tr.nextC.nxCharge}\n\n")
        self.s_out.insert('end', out)
        self.s_out.see('end')

    def _sim_apply(self):
        if self._last_sim_result is None:
            messagebox.showinfo("提示", "请先模拟一回合"); return
        tr = self._last_sim_result
        def fill(ctrl, v): ctrl.delete(0, 'end'); ctrl.insert(0, str(v))
        fill(self.s_p_dd, format_dd_units(tr.nextP.dd))
        fill(self.s_c_dd, format_dd_units(tr.nextC.dd))
        fill(self.s_p_l, tr.nextP.lightning); fill(self.s_c_l, tr.nextC.lightning)
        fill(self.s_p_b, tr.nextP.bombLayers); fill(self.s_c_b, tr.nextC.bombLayers)
        fill(self.s_p_nx, tr.nextP.nxCharge); fill(self.s_c_nx, tr.nextC.nxCharge)
        fill(self.s_p_cu, tr.nextP.cloudUses); fill(self.s_c_cu, tr.nextC.cloudUses)
        fill(self.s_p_tu, tr.nextP.tianUses); fill(self.s_c_tu, tr.nextC.tianUses)
        fill(self.s_p_jy, "1" if tr.nextP.juyanBuff else "0")
        fill(self.s_c_jy, "1" if tr.nextC.juyanBuff else "0")
        fill(self.s_p_bu, tr.nextP.bombUses); fill(self.s_c_bu, tr.nextC.bombUses)
        self.s_out.insert('end', "[模拟] 已把上一次模拟的结果写回输入框。\n\n")
        self.s_out.see('end')

    def _sim_reset(self):
        for (ctrl, val) in [(self.s_p_dd, "0"), (self.s_c_dd, "0"),
                            (self.s_p_l, "0"), (self.s_c_l, "0"),
                            (self.s_p_b, "0"), (self.s_c_b, "0"),
                            (self.s_p_nx, "0"), (self.s_c_nx, "0"),
                            (self.s_p_cu, "0"), (self.s_c_cu, "0"),
                            (self.s_p_tu, "0"), (self.s_c_tu, "0"),
                            (self.s_p_jy, "0"), (self.s_c_jy, "0"),
                            (self.s_p_bu, "0"), (self.s_c_bu, "0")]:
            ctrl.delete(0, 'end'); ctrl.insert(0, val)
        self.s_pmove_var.set("Charge"); self.s_cmove_var.set("Charge")
        self.s_out.delete('1.0', 'end')
        self.s_out.insert('end', "[模拟] 已重置为默认开局状态。\n\n")

    # ============================================================
    # 日志 & 规则
    # ============================================================
    def _log(self, s: str):
        self.log.insert('end', s)
        self.log.see('end')

    def _busy(self, flag: bool):
        try:
            self.root.config(cursor="watch" if flag else "")
        except Exception:
            pass

    def show_rules(self):
        win = tk.Toplevel(self.root)
        win.title("完整规则与招式说明")
        win.geometry("780x620")
        txt = scrolledtext.ScrolledText(win, wrap='word', font=("Segoe UI", 10))
        txt.pack(fill='both', expand=True, padx=8, pady=8)
        txt.insert('1.0', RULES_TEXT)
        txt.config(state='disabled')


if __name__ == '__main__':
    root = tk.Tk()
    gui = DeideiGUI(root)
    root.mainloop()
