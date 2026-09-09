#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cctype>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#endif

using std::cin;
using std::cout;
using std::string;
using std::vector;

static constexpr int kDDDen = 6;
static constexpr int kDDOne = 6;

static int gcdInt(int a, int b) {
    if (a < 0) a = -a;
    if (b < 0) b = -b;
    while (b != 0) {
        int t = a % b;
        a = b;
        b = t;
    }
    return a == 0 ? 1 : a;
}

static string formatDD(int units) {
    if (units < 0) units = 0;
    int whole = units / kDDDen;
    int rem = units % kDDDen;
    if (rem == 0) return std::to_string(whole);
    int g = gcdInt(rem, kDDDen);
    rem /= g;
    int den = kDDDen / g;
    if (whole == 0) return std::to_string(rem) + "/" + std::to_string(den);
    return std::to_string(whole) + "+" + std::to_string(rem) + "/" + std::to_string(den);
}

static string trimCopy(const string& s) {
    size_t b = 0;
    while (b < s.size() && std::isspace(static_cast<unsigned char>(s[b])) != 0) b++;
    size_t e = s.size();
    while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1])) != 0) e--;
    return s.substr(b, e - b);
}

static string toLowerCopy(string s) {
    for (char& ch : s) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    return s;
}

enum class Outcome : int {
    Continue = 0,
    PlayerWin = 1,
    CpuWin = 2,
    Draw = 3
};

enum class Move : int {
    Charge,
    Bi,
    Def,
    Three,
    ThreeDef,
    BigBi,
    Reflect,
    Suicide,
    Cloud,
    Bomb,
    Xiao,
    Pragon,
    PragonDef,
    Volvo,
    VolvoDef,
    RotateThree,
    XiaoBei,
    FlipVolvo,
    Shell,
    Absorb,
    NieXiang,
    NieXiangDef,
    JuYan,
    TianLiJun,
    ZhangXinWei,
    LiQiang,
    BombPragon,
    BombVolvo,
    BombFlipVolvo,
    FreeThree,
    FreeRotateThree
};

static bool isAttackMove(Move m) {
    switch (m) {
        case Move::Xiao:
        case Move::Bi:
        case Move::Pragon:
        case Move::Three:
        case Move::NieXiang:
        case Move::Volvo:
        case Move::BigBi:
        case Move::RotateThree:
        case Move::XiaoBei:
        case Move::FlipVolvo:
        case Move::Shell:
        case Move::BombPragon:
        case Move::BombVolvo:
        case Move::BombFlipVolvo:
        case Move::FreeThree:
        case Move::FreeRotateThree:
            return true;
        default:
            return false;
    }
}

static bool isQuantumMove(Move m) {
    return m == Move::RotateThree || m == Move::FlipVolvo || m == Move::FreeRotateThree;
}

static bool isCounterMove(Move m) {
    return m == Move::Reflect || m == Move::Absorb || m == Move::Cloud || m == Move::Suicide;
}

struct PlayerState {
    int dd = 0;
    int lightning = 0;
    int cloudUses = 0;
    int bombUses = 0;
    int bombLayers = 0;
    std::array<int, 3> bombPending{};
    int tianUses = 0;
    bool juyanBuff = false;
    int nxCharge = 0;
    bool zhangUsed = false;
    bool liqUsed = false;
    bool hasHighAttackRecord = false;
    Move lastHighAttack = Move::Charge;
    Move lastMove = Move::Charge;
};

static int clampNonNeg(int x) {
    return x < 0 ? 0 : x;
}

static bool isHighAttackForZhang(Move eff) {
    switch (eff) {
        case Move::Pragon:
        case Move::Three:
        case Move::Volvo:
        case Move::BigBi:
        case Move::Shell:
        case Move::XiaoBei:
        case Move::RotateThree:
        case Move::FlipVolvo:
        case Move::NieXiang:
        case Move::BombPragon:
        case Move::BombVolvo:
        case Move::BombFlipVolvo:
        case Move::FreeThree:
        case Move::FreeRotateThree:
            return true;
        default:
            return false;
    }
}

static int attackPowerUnits(Move eff, bool xiaoEnhanced) {
    switch (eff) {
        case Move::Xiao: return 2;
        case Move::Bi: return 6;
        case Move::Pragon: return 12;
        case Move::Three: return 18;
        case Move::NieXiang: return 21;
        case Move::Volvo: return 24;
        case Move::BigBi: return 30;
        case Move::RotateThree: return 36;
        case Move::XiaoBei: return 42;
        case Move::FlipVolvo: return 48;
        case Move::Shell: return 60;
        case Move::BombPragon: return 12;
        case Move::BombVolvo: return 24;
        case Move::BombFlipVolvo: return 48;
        case Move::FreeThree: return 18;
        case Move::FreeRotateThree: return 36;
        default:
            if (xiaoEnhanced && eff == Move::Xiao) return 2;
            return 0;
    }
}

static bool isShellLike(Move eff) {
    return eff == Move::Shell || eff == Move::XiaoBei;
}

static bool isUnreflectable(Move eff) {
    return eff == Move::Shell || eff == Move::XiaoBei;
}

static bool isUnabsorbable(Move eff) {
    if (eff == Move::Shell || eff == Move::XiaoBei || eff == Move::NieXiang) return true;
    if (eff == Move::RotateThree || eff == Move::FlipVolvo || eff == Move::FreeRotateThree) return true;
    return false;
}

static bool isAbsorbableAttack(Move eff, bool xiaoEnhanced) {
    if (!isAttackMove(eff)) return false;
    if (isUnabsorbable(eff)) return false;
    if (eff == Move::Volvo || eff == Move::BombVolvo || eff == Move::BombFlipVolvo || eff == Move::FlipVolvo || eff == Move::RotateThree) return false;
    if (xiaoEnhanced && eff == Move::Xiao) return true;
    if (eff == Move::Xiao || eff == Move::Bi || eff == Move::Pragon || eff == Move::Three || eff == Move::BigBi || eff == Move::BombPragon || eff == Move::FreeThree) return true;
    return false;
}

static bool isBlockedByAnyDefense(Move eff, bool xiaoEnhanced) {
    if (xiaoEnhanced && eff == Move::Xiao) return false;
    return eff == Move::Xiao;
}

static string moveName(Move m) {
    switch (m) {
        case Move::Charge: return "攒";
        case Move::Bi: return "Bi";
        case Move::Def: return "防御";
        case Move::Three: return "三雷";
        case Move::ThreeDef: return "三雷防";
        case Move::BigBi: return "大Bi";
        case Move::Reflect: return "反弹";
        case Move::Suicide: return "自杀";
        case Move::Cloud: return "云";
        case Move::Bomb: return "炸药";
        case Move::Xiao: return "削";
        case Move::Pragon: return "pragon";
        case Move::PragonDef: return "pragon防";
        case Move::Volvo: return "沃尔沃";
        case Move::VolvoDef: return "沃尔沃防";
        case Move::RotateThree: return "旋转三雷";
        case Move::XiaoBei: return "小贝";
        case Move::FlipVolvo: return "翻转沃尔沃";
        case Move::Shell: return "扇贝";
        case Move::Absorb: return "吸收";
        case Move::NieXiang: return "聂湘";
        case Move::NieXiangDef: return "聂湘防";
        case Move::JuYan: return "距喦";
        case Move::TianLiJun: return "田立军";
        case Move::ZhangXinWei: return "张新伟";
        case Move::LiQiang: return "历强";
        case Move::BombPragon: return "pragon(炸药层)";
        case Move::BombVolvo: return "沃尔沃(炸药层)";
        case Move::BombFlipVolvo: return "翻转沃尔沃(炸药层)";
        case Move::FreeThree: return "三雷(雷电)";
        case Move::FreeRotateThree: return "旋转三雷(雷电)";
    }
    return "未知";
}

struct Action {
    Move declared = Move::Charge;
    Move effective = Move::Charge;
    bool xiaoEnhanced = false;

    int ddCost = 0;
    int bombLayerCost = 0;
    int lightningCost = 0;
    int nxCost = 0;

    bool triggersLiQiangWin = false;
    bool liQiangAsCharge = false;
};

static int ddCostUnitsForMove(const PlayerState& self, Move m) {
    switch (m) {
        case Move::Charge: return 0;
        case Move::Bi: return 6;
        case Move::Def: return 0;
        case Move::Three: return 18;
        case Move::ThreeDef: return 0;
        case Move::BigBi: return 30;
        case Move::Reflect: return 6;
        case Move::Suicide: return 0;
        case Move::Cloud: return self.cloudUses == 0 ? 0 : 6;
        case Move::Bomb: return 6;
        case Move::Xiao: return 2;
        case Move::Pragon: return 12;
        case Move::PragonDef: return 0;
        case Move::Volvo: return 24;
        case Move::VolvoDef: return 0;
        case Move::RotateThree: return 36;
        case Move::XiaoBei: return 42;
        case Move::FlipVolvo: return 48;
        case Move::Shell: return 60;
        case Move::Absorb: return 6;
        case Move::NieXiang: return 0;
        case Move::NieXiangDef: return 0;
        case Move::JuYan: return 0;
        case Move::TianLiJun: return self.tianUses == 0 ? 0 : 3;
        case Move::ZhangXinWei: return 0;
        case Move::LiQiang: return 0;
        case Move::BombPragon: return 0;
        case Move::BombVolvo: return 0;
        case Move::BombFlipVolvo: return 0;
        case Move::FreeThree: return 0;
        case Move::FreeRotateThree: return 0;
    }
    return 0;
}

static bool isLegalMove(const PlayerState& self, const PlayerState& opp, Move m) {
    if (m == Move::ZhangXinWei) {
        return !self.zhangUsed && self.hasHighAttackRecord;
    }
    if (m == Move::LiQiang) {
        return !self.liqUsed;
    }
    if (m == Move::NieXiang) {
        return self.nxCharge >= 4;
    }
    if (m == Move::BombPragon) {
        return self.bombLayers >= 1;
    }
    if (m == Move::BombVolvo) {
        return self.bombLayers >= 2;
    }
    if (m == Move::BombFlipVolvo) {
        return self.bombLayers >= 4;
    }
    if (m == Move::FreeThree) {
        return self.lightning >= 3;
    }
    if (m == Move::FreeRotateThree) {
        return self.lightning >= 6;
    }
    int cost = ddCostUnitsForMove(self, m);
    if (self.dd < cost) return false;
    if (m == Move::Def || m == Move::ThreeDef || m == Move::PragonDef || m == Move::VolvoDef || m == Move::NieXiangDef) {
        (void)opp;
        return true;
    }
    return true;
}

static vector<Move> listLegalMoves(const PlayerState& self, const PlayerState& opp) {
    static const std::array<Move, 31> allMoves = {
        Move::Charge, Move::Bi, Move::Def, Move::Three, Move::ThreeDef, Move::BigBi, Move::Reflect, Move::Suicide,
        Move::Cloud, Move::Bomb, Move::Xiao, Move::Pragon, Move::PragonDef, Move::Volvo, Move::VolvoDef,
        Move::RotateThree, Move::XiaoBei, Move::FlipVolvo, Move::Shell, Move::Absorb, Move::NieXiang,
        Move::NieXiangDef, Move::JuYan, Move::TianLiJun, Move::ZhangXinWei, Move::LiQiang,
        Move::BombPragon, Move::BombVolvo, Move::BombFlipVolvo, Move::FreeThree, Move::FreeRotateThree
    };
    vector<Move> ms;
    for (Move m : allMoves) {
        if (isLegalMove(self, opp, m)) ms.push_back(m);
    }
    return ms;
}

static Action buildAction(const PlayerState& self, const PlayerState& opp, Move declared) {
    Action a;
    a.declared = declared;
    a.effective = declared;

    if (declared == Move::LiQiang) {
        a.triggersLiQiangWin = (opp.lastMove == declared);
        a.liQiangAsCharge = !a.triggersLiQiangWin;
        if (a.liQiangAsCharge) a.effective = Move::Charge;
    }

    if (declared == Move::ZhangXinWei) {
        a.effective = self.lastHighAttack;
    } else if (declared == Move::BombPragon) {
        a.effective = Move::Pragon;
    } else if (declared == Move::BombVolvo) {
        a.effective = Move::Volvo;
    } else if (declared == Move::BombFlipVolvo) {
        a.effective = Move::FlipVolvo;
    } else if (declared == Move::FreeThree) {
        a.effective = Move::Three;
    } else if (declared == Move::FreeRotateThree) {
        a.effective = Move::RotateThree;
    }

    a.ddCost = ddCostUnitsForMove(self, declared);

    if (declared == Move::Xiao && self.juyanBuff) {
        a.xiaoEnhanced = true;
        a.ddCost = 0;
    }

    if (declared == Move::BombPragon) a.bombLayerCost = 1;
    if (declared == Move::BombVolvo) a.bombLayerCost = 2;
    if (declared == Move::BombFlipVolvo) a.bombLayerCost = 4;

    if (declared == Move::FreeThree) a.lightningCost = 3;
    if (declared == Move::FreeRotateThree) a.lightningCost = 6;

    if (declared == Move::NieXiang) a.nxCost = 4;

    return a;
}

static vector<Move> interpretations(const Action& a) {
    if (a.effective == Move::RotateThree) return {Move::Three, Move::Suicide};
    if (a.effective == Move::FlipVolvo) return {Move::Volvo, Move::Suicide};
    return {a.effective};
}

static bool blocksAttack(const PlayerState& defender, const Action& defAct, Move defMove, Move atkMove, bool atkXiaoEnhanced) {
    if (!isAttackMove(atkMove)) return false;
    if (atkMove == Move::Shell || atkMove == Move::XiaoBei) return false;

    if (atkMove == Move::BigBi) {
        if (defMove == Move::TianLiJun) return true;
        return false;
    }

    if (atkMove == Move::Three) {
        if (defMove == Move::ThreeDef) return true;
        if (defMove == Move::TianLiJun) return true;
        if (defMove == Move::Bomb) {
            int x = defender.bombUses + 1;
            if (x > 4) x = 4;
            int threshold = (x - 1) * kDDOne;
            return attackPowerUnits(atkMove, atkXiaoEnhanced) <= threshold;
        }
        if (isBlockedByAnyDefense(atkMove, atkXiaoEnhanced)) return defMove == Move::JuYan;
        return false;
    }

    if (atkMove == Move::Volvo) {
        if (defMove == Move::VolvoDef) return true;
        if (defMove == Move::TianLiJun) return true;
        return false;
    }

    if (atkMove == Move::Pragon) {
        if (defMove == Move::PragonDef) return true;
        if (defMove == Move::VolvoDef) return true;
        if (defMove == Move::TianLiJun) return true;
        if (defMove == Move::Bomb) {
            int x = defender.bombUses + 1;
            if (x > 4) x = 4;
            int threshold = (x - 1) * kDDOne;
            return attackPowerUnits(atkMove, atkXiaoEnhanced) <= threshold;
        }
        if (isBlockedByAnyDefense(atkMove, atkXiaoEnhanced)) return defMove == Move::JuYan;
        return false;
    }

    if (atkMove == Move::Bi) {
        if (defMove == Move::Def) return true;
        if (defMove == Move::TianLiJun) return true;
        if (defMove == Move::Bomb) {
            int x = defender.bombUses + 1;
            if (x > 4) x = 4;
            int threshold = (x - 1) * kDDOne;
            return attackPowerUnits(atkMove, atkXiaoEnhanced) <= threshold;
        }
        if (isBlockedByAnyDefense(atkMove, atkXiaoEnhanced)) return defMove != Move::Reflect && defMove != Move::Absorb && defMove != Move::Cloud && defMove != Move::Suicide;
        return false;
    }

    if (atkMove == Move::Xiao) {
        if (atkXiaoEnhanced) {
            return defMove == Move::JuYan;
        }
        if (defMove == Move::JuYan) return true;
        if (defMove == Move::Def || defMove == Move::ThreeDef || defMove == Move::PragonDef || defMove == Move::VolvoDef || defMove == Move::NieXiangDef || defMove == Move::TianLiJun) return true;
        if (defMove == Move::Bomb) {
            int x = defender.bombUses + 1;
            if (x > 4) x = 4;
            int threshold = (x - 1) * kDDOne;
            return attackPowerUnits(atkMove, atkXiaoEnhanced) <= threshold;
        }
        return false;
    }

    if (atkMove == Move::NieXiang) {
        if (defMove == Move::NieXiangDef) return true;
        if (defMove == Move::TianLiJun) return true;
        return false;
    }

    if (defMove == Move::TianLiJun) return true;
    if (defMove == Move::Bomb) {
        int x = defender.bombUses + 1;
        if (x > 4) x = 4;
        int threshold = (x - 1) * kDDOne;
        return attackPowerUnits(atkMove, atkXiaoEnhanced) <= threshold;
    }

    (void)defAct;
    return false;
}

static std::pair<Outcome, std::pair<int, int>> resolveNoQuantum(const PlayerState& p0, const PlayerState& c0, const Action& pAct, const Action& cAct, Move pEff, Move cEff) {
    bool pXiaoEnhanced = pAct.xiaoEnhanced && pEff == Move::Xiao;
    bool cXiaoEnhanced = cAct.xiaoEnhanced && cEff == Move::Xiao;

    if (pAct.triggersLiQiangWin && cAct.triggersLiQiangWin) return {Outcome::Draw, {0, 0}};
    if (pAct.triggersLiQiangWin) return {Outcome::PlayerWin, {0, 0}};
    if (cAct.triggersLiQiangWin) return {Outcome::CpuWin, {0, 0}};

    if (pEff == Move::Suicide && cEff == Move::Suicide) return {Outcome::Draw, {0, 0}};
    if (pEff == Move::Suicide) {
        if (cEff == Move::Reflect || cEff == Move::Absorb || cEff == Move::Cloud) return {Outcome::PlayerWin, {0, 0}};
        return {Outcome::CpuWin, {0, 0}};
    }
    if (cEff == Move::Suicide) {
        if (pEff == Move::Reflect || pEff == Move::Absorb || pEff == Move::Cloud) return {Outcome::CpuWin, {0, 0}};
        return {Outcome::PlayerWin, {0, 0}};
    }

    if (pEff == Move::TianLiJun && (cEff == Move::Reflect || cEff == Move::Absorb || cEff == Move::Cloud)) return {Outcome::CpuWin, {0, 0}};
    if (cEff == Move::TianLiJun && (pEff == Move::Reflect || pEff == Move::Absorb || pEff == Move::Cloud)) return {Outcome::PlayerWin, {0, 0}};

    if (pEff == Move::Reflect && !isUnreflectable(cEff) && isAttackMove(cEff)) return {Outcome::PlayerWin, {0, 0}};
    if (cEff == Move::Reflect && !isUnreflectable(pEff) && isAttackMove(pEff)) return {Outcome::CpuWin, {0, 0}};

    int ddGainP = 0;
    int ddGainC = 0;

    if (pEff == Move::Absorb) {
        if (cEff == Move::Charge || cAct.liQiangAsCharge) {
            ddGainP += kDDOne;
            return {Outcome::Continue, {ddGainP, ddGainC}};
        }
        if (isAbsorbableAttack(cEff, cXiaoEnhanced)) {
            ddGainP += ddCostUnitsForMove(c0, cAct.declared == Move::ZhangXinWei ? cAct.effective : cAct.declared);
            return {Outcome::Continue, {ddGainP, ddGainC}};
        }
    }
    if (cEff == Move::Absorb) {
        if (pEff == Move::Charge || pAct.liQiangAsCharge) {
            ddGainC += kDDOne;
            return {Outcome::Continue, {ddGainP, ddGainC}};
        }
        if (isAbsorbableAttack(pEff, pXiaoEnhanced)) {
            ddGainC += ddCostUnitsForMove(p0, pAct.declared == Move::ZhangXinWei ? pAct.effective : pAct.declared);
            return {Outcome::Continue, {ddGainP, ddGainC}};
        }
    }

    if (pEff == Move::Cloud) {
        if (cEff == Move::Charge || cAct.liQiangAsCharge) return {Outcome::Continue, {ddGainP, ddGainC}};
        if (isAbsorbableAttack(cEff, cXiaoEnhanced)) return {Outcome::Continue, {ddGainP, ddGainC}};
    }
    if (cEff == Move::Cloud) {
        if (pEff == Move::Charge || pAct.liQiangAsCharge) return {Outcome::Continue, {ddGainP, ddGainC}};
        if (isAbsorbableAttack(pEff, pXiaoEnhanced)) return {Outcome::Continue, {ddGainP, ddGainC}};
    }

    if (pEff == Move::XiaoBei && (cEff == Move::Charge || cAct.liQiangAsCharge)) return {Outcome::CpuWin, {0, 0}};
    if (cEff == Move::XiaoBei && (pEff == Move::Charge || pAct.liQiangAsCharge)) return {Outcome::PlayerWin, {0, 0}};

    if (pEff == Move::Shell && cEff == Move::XiaoBei) return {Outcome::Continue, {0, 0}};
    if (cEff == Move::Shell && pEff == Move::XiaoBei) return {Outcome::Continue, {0, 0}};
    if (pEff == Move::Shell && cEff == Move::Shell) return {Outcome::Continue, {0, 0}};
    if (pEff == Move::XiaoBei && cEff == Move::XiaoBei) return {Outcome::Continue, {0, 0}};

    bool pIsAtk = isAttackMove(pEff);
    bool cIsAtk = isAttackMove(cEff);

    if (pIsAtk && cIsAtk) {
        int pPow = attackPowerUnits(pEff, pXiaoEnhanced);
        int cPow = attackPowerUnits(cEff, cXiaoEnhanced);
        if (pPow == cPow) return {Outcome::Continue, {0, 0}};
        return pPow > cPow ? std::make_pair(Outcome::PlayerWin, std::make_pair(0, 0)) : std::make_pair(Outcome::CpuWin, std::make_pair(0, 0));
    }

    if (pIsAtk && !cIsAtk) {
        if (blocksAttack(c0, cAct, cEff, pEff, pXiaoEnhanced)) return {Outcome::Continue, {0, 0}};
        return {Outcome::PlayerWin, {0, 0}};
    }
    if (cIsAtk && !pIsAtk) {
        if (blocksAttack(p0, pAct, pEff, cEff, cXiaoEnhanced)) return {Outcome::Continue, {0, 0}};
        return {Outcome::CpuWin, {0, 0}};
    }

    return {Outcome::Continue, {0, 0}};
}

static Outcome selectQuantumOutcome(const PlayerState& p0, const PlayerState& c0, const Action& pAct, const Action& cAct, int& ddGainP, int& ddGainC) {
    vector<Move> pInts = interpretations(pAct);
    vector<Move> cInts = interpretations(cAct);

    struct Cell {
        Outcome out;
        int gp;
        int gc;
        int up;
        int uc;
    };

    vector<vector<Cell>> cells(pInts.size(), vector<Cell>(cInts.size()));
    for (size_t i = 0; i < pInts.size(); ++i) {
        for (size_t j = 0; j < cInts.size(); ++j) {
            auto r = resolveNoQuantum(p0, c0, pAct, cAct, pInts[i], cInts[j]);
            Outcome out = r.first;
            int gp = r.second.first;
            int gc = r.second.second;
            int up = 0;
            int uc = 0;
            if (out == Outcome::PlayerWin) { up = 1; uc = -1; }
            else if (out == Outcome::CpuWin) { up = -1; uc = 1; }
            else if (out == Outcome::Draw) { up = 0; uc = 0; }
            else { up = 0; uc = 0; }
            cells[i][j] = Cell{out, gp, gc, up, uc};
        }
    }

    vector<std::pair<size_t, size_t>> equilibria;
    for (size_t i = 0; i < pInts.size(); ++i) {
        for (size_t j = 0; j < cInts.size(); ++j) {
            int up = cells[i][j].up;
            int uc = cells[i][j].uc;
            bool pBest = true;
            for (size_t ii = 0; ii < pInts.size(); ++ii) {
                if (cells[ii][j].up > up) { pBest = false; break; }
            }
            if (!pBest) continue;
            bool cBest = true;
            for (size_t jj = 0; jj < cInts.size(); ++jj) {
                if (cells[i][jj].uc > uc) { cBest = false; break; }
            }
            if (!cBest) continue;
            equilibria.push_back({i, j});
        }
    }

    size_t bi = 0, bj = 0;
    if (!equilibria.empty()) {
        bi = equilibria[0].first;
        bj = equilibria[0].second;
    } else {
        bi = 0;
        bj = 0;
        int bestScore = std::numeric_limits<int>::min();
        for (size_t i = 0; i < pInts.size(); ++i) {
            for (size_t j = 0; j < cInts.size(); ++j) {
                int score = cells[i][j].up + cells[i][j].uc;
                if (score > bestScore) { bestScore = score; bi = i; bj = j; }
            }
        }
    }

    ddGainP = cells[bi][bj].gp;
    ddGainC = cells[bi][bj].gc;
    return cells[bi][bj].out;
}

static void endOfTurnBomb(PlayerState& s) {
    s.bombLayers += s.bombPending[0];
    s.bombPending[0] = s.bombPending[1];
    s.bombPending[1] = s.bombPending[2];
    s.bombPending[2] = 0;
    s.bombLayers = clampNonNeg(s.bombLayers);
}

struct TurnResult {
    Outcome outcome = Outcome::Continue;
    PlayerState nextP;
    PlayerState nextC;
    int ddGainP = 0;
    int ddGainC = 0;
};

static TurnResult simulateTurn(const PlayerState& p0, const PlayerState& c0, Move pMove, Move cMove) {
    TurnResult tr;
    tr.nextP = p0;
    tr.nextC = c0;

    Action pAct = buildAction(p0, c0, pMove);
    Action cAct = buildAction(c0, p0, cMove);

    if (!isLegalMove(p0, c0, pMove) || !isLegalMove(c0, p0, cMove)) {
        tr.outcome = Outcome::Continue;
        return tr;
    }

    tr.nextP.dd -= pAct.ddCost;
    tr.nextC.dd -= cAct.ddCost;

    tr.nextP.dd = clampNonNeg(tr.nextP.dd);
    tr.nextC.dd = clampNonNeg(tr.nextC.dd);

    tr.nextP.bombLayers -= pAct.bombLayerCost;
    tr.nextC.bombLayers -= cAct.bombLayerCost;
    tr.nextP.bombLayers = clampNonNeg(tr.nextP.bombLayers);
    tr.nextC.bombLayers = clampNonNeg(tr.nextC.bombLayers);

    tr.nextP.lightning -= pAct.lightningCost;
    tr.nextC.lightning -= cAct.lightningCost;
    tr.nextP.lightning = clampNonNeg(tr.nextP.lightning);
    tr.nextC.lightning = clampNonNeg(tr.nextC.lightning);

    tr.nextP.nxCharge -= pAct.nxCost;
    tr.nextC.nxCharge -= cAct.nxCost;
    tr.nextP.nxCharge = clampNonNeg(tr.nextP.nxCharge);
    tr.nextC.nxCharge = clampNonNeg(tr.nextC.nxCharge);

    if (pMove == Move::ZhangXinWei) tr.nextP.zhangUsed = true;
    if (cMove == Move::ZhangXinWei) tr.nextC.zhangUsed = true;
    if (pMove == Move::LiQiang) tr.nextP.liqUsed = true;
    if (cMove == Move::LiQiang) tr.nextC.liqUsed = true;

    if (pMove == Move::Cloud) {
        tr.nextP.cloudUses += 1;
        tr.nextP.lightning += 1;
    }
    if (cMove == Move::Cloud) {
        tr.nextC.cloudUses += 1;
        tr.nextC.lightning += 1;
    }

    if (pMove == Move::Bomb) {
        tr.nextP.bombUses += 1;
        tr.nextP.bombPending[2] += 1;
    }
    if (cMove == Move::Bomb) {
        tr.nextC.bombUses += 1;
        tr.nextC.bombPending[2] += 1;
    }

    if (pMove == Move::TianLiJun) tr.nextP.tianUses += 1;
    if (cMove == Move::TianLiJun) tr.nextC.tianUses += 1;

    if (pMove == Move::JuYan) tr.nextP.juyanBuff = true;
    if (cMove == Move::JuYan) tr.nextC.juyanBuff = true;

    if (pMove == Move::Def) tr.nextP.nxCharge += 1;
    if (cMove == Move::Def) tr.nextC.nxCharge += 1;

    int ddGainP = 0;
    int ddGainC = 0;
    Outcome out = selectQuantumOutcome(p0, c0, pAct, cAct, ddGainP, ddGainC);

    tr.ddGainP = ddGainP;
    tr.ddGainC = ddGainC;

    tr.nextP.dd += ddGainP;
    tr.nextC.dd += ddGainC;

    bool pCharged = (pAct.effective == Move::Charge);
    bool cCharged = (cAct.effective == Move::Charge);
    bool pChargeDenied = false;
    bool cChargeDenied = false;

    if (pCharged && (cAct.effective == Move::Absorb || cAct.effective == Move::Cloud)) pChargeDenied = true;
    if (cCharged && (pAct.effective == Move::Absorb || pAct.effective == Move::Cloud)) cChargeDenied = true;

    if (pCharged && !pChargeDenied) tr.nextP.dd += kDDOne;
    if (cCharged && !cChargeDenied) tr.nextC.dd += kDDOne;

    if (pAct.effective == Move::TianLiJun && (cCharged)) tr.nextC.dd = 0;
    if (cAct.effective == Move::TianLiJun && (pCharged)) tr.nextP.dd = 0;

    if (pMove == Move::Def) {
        if (cAct.effective == Move::Bi || (cAct.effective == Move::Xiao && !cAct.xiaoEnhanced)) tr.nextP.nxCharge += 1;
    }
    if (cMove == Move::Def) {
        if (pAct.effective == Move::Bi || (pAct.effective == Move::Xiao && !pAct.xiaoEnhanced)) tr.nextC.nxCharge += 1;
    }

    if (pMove == Move::Xiao && p0.juyanBuff) tr.nextP.juyanBuff = false;
    if (cMove == Move::Xiao && c0.juyanBuff) tr.nextC.juyanBuff = false;

    if (isHighAttackForZhang(pAct.effective)) {
        tr.nextP.hasHighAttackRecord = true;
        tr.nextP.lastHighAttack = pAct.effective;
    }
    if (isHighAttackForZhang(cAct.effective)) {
        tr.nextC.hasHighAttackRecord = true;
        tr.nextC.lastHighAttack = cAct.effective;
    }

    tr.nextP.lastMove = pMove;
    tr.nextC.lastMove = cMove;

    endOfTurnBomb(tr.nextP);
    endOfTurnBomb(tr.nextC);

    tr.nextP.dd = clampNonNeg(tr.nextP.dd);
    tr.nextC.dd = clampNonNeg(tr.nextC.dd);

    tr.outcome = out;
    return tr;
}

static double valueToReferenceWinRate(double v) {
    double w = 0.5 * (v + 1.0);
    if (w < 0.0) w = 0.0;
    if (w > 1.0) w = 1.0;
    return w;
}

static double evaluateStateHeuristic(const PlayerState& p, const PlayerState& c) {
    double ddDiff = static_cast<double>(p.dd - c.dd) / 30.0;
    double layerDiff = static_cast<double>(p.bombLayers - c.bombLayers) / 4.0;
    double lightningDiff = static_cast<double>(p.lightning - c.lightning) / 6.0;
    double nxDiff = static_cast<double>(p.nxCharge - c.nxCharge) / 4.0;
    double buffDiff = (p.juyanBuff ? 0.2 : 0.0) - (c.juyanBuff ? 0.2 : 0.0);
    double specialDiff = (p.hasHighAttackRecord ? 0.05 : 0.0) - (c.hasHighAttackRecord ? 0.05 : 0.0);

    double s = 1.4 * ddDiff + 0.8 * layerDiff + 0.4 * lightningDiff + 0.4 * nxDiff + buffDiff + specialDiff;
    return std::tanh(s);
}

static vector<double> regretMatchingStrategy(const vector<double>& regrets) {
    vector<double> s(regrets.size(), 0.0);
    double sumPos = 0.0;
    for (size_t i = 0; i < regrets.size(); ++i) {
        double r = regrets[i];
        if (r > 0.0) {
            s[i] = r;
            sumPos += r;
        }
    }
    if (sumPos <= 0.0) {
        double u = 1.0 / static_cast<double>(regrets.size());
        std::fill(s.begin(), s.end(), u);
        return s;
    }
    for (double& v : s) v /= sumPos;
    return s;
}

static double expectedValue(const vector<double>& p, const vector<double>& q, const vector<vector<double>>& A) {
    double v = 0.0;
    for (size_t i = 0; i < p.size(); ++i) {
        for (size_t j = 0; j < q.size(); ++j) v += p[i] * A[i][j] * q[j];
    }
    return v;
}

struct MatrixGameSolution {
    vector<double> playerStrategy;
    vector<double> cpuStrategy;
    double value = 0.0;
};

static MatrixGameSolution solveZeroSumMatrixGameRegretMatching(const vector<vector<double>>& A, int iterations) {
    const int m = static_cast<int>(A.size());
    const int n = static_cast<int>(A[0].size());

    // adapt iterations to problem size to avoid unnecessary work for small action sets
    const int kMaxMoves = 31 * 31;
    int effIterations = std::max(600, static_cast<int>((static_cast<double>(iterations) * (m * n)) / static_cast<double>(kMaxMoves)));
    if (effIterations > iterations) effIterations = iterations;

    vector<double> rp(m, 0.0), rc(n, 0.0);
    vector<double> sp(m, 0.0), sc(n, 0.0);

    vector<double> p(m, 1.0 / m);
    vector<double> q(n, 1.0 / n);

    vector<double> prevP = p, prevQ = q;
    vector<double> uP(m, 0.0);
    vector<double> uC(n, 0.0);

    const double convergeTol = 1e-6;
    const int patience = 200; // require small change to persist
    int smallChangeCount = 0;
    int actualIters = 0;

    for (int t = 0; t < effIterations; ++t) {
        ++actualIters;
        p = regretMatchingStrategy(rp);
        q = regretMatchingStrategy(rc);

        double change = 0.0;
        for (int i = 0; i < m; ++i) change += std::fabs(p[i] - prevP[i]);
        for (int j = 0; j < n; ++j) change += std::fabs(q[j] - prevQ[j]);

        if (change < convergeTol) smallChangeCount++; else smallChangeCount = 0;
        prevP = p; prevQ = q;

        for (int i = 0; i < m; ++i) sp[i] += p[i];
        for (int j = 0; j < n; ++j) sc[j] += q[j];

        for (int i = 0; i < m; ++i) {
            double s = 0.0;
            for (int j = 0; j < n; ++j) s += A[i][j] * q[j];
            uP[i] = s;
        }
        double evP = 0.0;
        for (int i = 0; i < m; ++i) evP += p[i] * uP[i];
        for (int i = 0; i < m; ++i) rp[i] += uP[i] - evP;

        for (int j = 0; j < n; ++j) {
            double s = 0.0;
            for (int i = 0; i < m; ++i) s += p[i] * A[i][j];
            uC[j] = s;
        }
        double evC = 0.0;
        for (int j = 0; j < n; ++j) evC += q[j] * uC[j];
        for (int j = 0; j < n; ++j) rc[j] += evC - uC[j];

        // early stop when strategies have converged for enough consecutive iterations
        if (smallChangeCount >= patience) break;
    }

    // normalize averaged strategies by actual iterations performed
    int itersUsed = std::max(1, actualIters);
    for (double& v : sp) v /= static_cast<double>(itersUsed);
    for (double& v : sc) v /= static_cast<double>(itersUsed);

    double spSum = std::accumulate(sp.begin(), sp.end(), 0.0);
    double scSum = std::accumulate(sc.begin(), sc.end(), 0.0);
    if (spSum > 0.0) for (double& v : sp) v /= spSum;
    if (scSum > 0.0) for (double& v : sc) v /= scSum;

    double value = expectedValue(sp, sc, A);
    return MatrixGameSolution{sp, sc, value};
}

struct LocalGTO {
    double gamma = 0.97;
    int iterations = 3000;

    MatrixGameSolution solve(const PlayerState& p, const PlayerState& c) const {
        vector<Move> pMoves = listLegalMoves(p, c);
        vector<Move> cMoves = listLegalMoves(c, p);

        vector<vector<double>> A(pMoves.size(), vector<double>(cMoves.size(), 0.0));
        for (size_t i = 0; i < pMoves.size(); ++i) {
            for (size_t j = 0; j < cMoves.size(); ++j) {
                TurnResult tr = simulateTurn(p, c, pMoves[i], cMoves[j]);
                double payoff = 0.0;
                if (tr.outcome == Outcome::PlayerWin) payoff = 1.0;
                else if (tr.outcome == Outcome::CpuWin) payoff = -1.0;
                else if (tr.outcome == Outcome::Draw) payoff = 0.0;
                else payoff = gamma * evaluateStateHeuristic(tr.nextP, tr.nextC);
                A[i][j] = payoff;
            }
        }

        MatrixGameSolution sol = solveZeroSumMatrixGameRegretMatching(A, iterations);

        vector<double> psAll(31, 0.0);
        vector<double> csAll(31, 0.0);
        for (size_t i = 0; i < pMoves.size(); ++i) psAll[static_cast<int>(pMoves[i])] = sol.playerStrategy[i];
        for (size_t j = 0; j < cMoves.size(); ++j) csAll[static_cast<int>(cMoves[j])] = sol.cpuStrategy[j];
        sol.playerStrategy = psAll;
        sol.cpuStrategy = csAll;

        return sol;
    }
};

static Move sampleFromDist(const vector<Move>& moves, const vector<double>& probs, std::mt19937& rng) {
    double sum = 0.0;
    for (double v : probs) sum += v;
    if (sum <= 1e-12) {
        std::uniform_int_distribution<int> uni(0, static_cast<int>(moves.size()) - 1);
        return moves[uni(rng)];
    }
    std::uniform_real_distribution<double> u01(0.0, 1.0);
    double r = u01(rng);
    double acc = 0.0;
    for (size_t i = 0; i < moves.size(); ++i) {
        acc += probs[i] / sum;
        if (r <= acc) return moves[i];
    }
    return moves.empty() ? Move::Charge : moves.back();
}

static Move chooseEasyMove(const PlayerState& cpu, const PlayerState& player, std::mt19937& rng) {
    vector<Move> legal = listLegalMoves(cpu, player);

    std::uniform_real_distribution<double> u01(0.0, 1.0);
    double r = u01(rng);

    if (cpu.dd >= 60 && r < 0.6) return Move::Shell;
    if (cpu.dd >= 42 && r < 0.15) return Move::XiaoBei;
    if (cpu.dd >= 48 && r < 0.10) return Move::FlipVolvo;
    if (cpu.dd >= 36 && r < 0.10) return Move::RotateThree;
    if (cpu.dd >= 30 && r < 0.12) return Move::BigBi;
    if (cpu.dd >= 24 && r < 0.12) return Move::Volvo;
    if (cpu.dd >= 18 && r < 0.12) return Move::Three;
    if (cpu.dd >= 12 && r < 0.10) return Move::Pragon;
    if (cpu.dd >= 6 && r < 0.10) return Move::Reflect;

    vector<Move> pool;
    for (Move m : {Move::Charge, Move::Xiao, Move::Bi, Move::Def, Move::Cloud, Move::Bomb, Move::Absorb, Move::JuYan}) {
        if (std::find(legal.begin(), legal.end(), m) != legal.end()) pool.push_back(m);
    }
    if (!pool.empty()) {
        std::uniform_int_distribution<int> uni(0, static_cast<int>(pool.size()) - 1);
        return pool[uni(rng)];
    }
    std::uniform_int_distribution<int> uni(0, static_cast<int>(legal.size()) - 1);
    return legal[uni(rng)];
}

static void printRules() {
    cout << "==================== 规则说明（新版本） ====================\n";
    cout << "1) 资源：双方拥有DD(允许分数DD，例如1/3、1/2)。\n";
    cout << "2) 回合制：双方每回合同步出招。\n";
    cout << "3) 胜负：任意攻击命中(未被防御/反弹/吸收/云等反制)则立刻获胜。\n";
    cout << "4) 抵消：同类攻击相遇互相抵消，消耗不返还。\n";
    cout << "5) 强弱：不同类攻击相遇，强度(等效消耗)更高者获胜。\n";
    cout << "\n重要招式摘要：\n";
    cout << "- 攒：+1DD\n";
    cout << "- 削(1/3)：可被任意防御挡；距喦后下一次削变强化削(0)，只能被距喦挡\n";
    cout << "- Bi(1)：可被防御挡\n";
    cout << "- 三雷(3)：无视防御；可被三雷防/反弹克制\n";
    cout << "- pragon(2)：可被pragon防或更高级防挡\n";
    cout << "- 沃尔沃(4)：无视防御；可被沃尔沃防/反弹克制\n";
    cout << "- 大Bi(5)：无视所有防御/专属防；可被反弹克制；可被吸收/云克制\n";
    cout << "- 扇贝(10)：无视防御与反弹，不可被反弹/吸收/云\n";
    cout << "- 小贝(7)：等效扇贝(无视防御/反弹)，可与扇贝抵消；弱点：被攒击杀\n";
    cout << "- 反弹(1)：反杀常规攻击；被自杀与量子态克制\n";
    cout << "- 自杀(0)：克制反弹/吸收/云；其余情况自杀方输；双方自杀平局\n";
    cout << "- 吸收(1)：对攒使对方本回合攒无效；对(削~大Bi)成功防御并获得对方消耗DD\n";
    cout << "- 云：首次0之后每次1；效果同吸收但吸到的DD无人获得；每次+1雷电\n";
    cout << "  雷电：3层可免费三雷；6层可免费旋转三雷\n";
    cout << "- 旋转三雷(6)：量子态(三雷/自杀)，结算时取最有利解释\n";
    cout << "- 翻转沃尔沃(8)：量子态(沃尔沃/自杀)，结算时取最有利解释\n";
    cout << "- 炸药(1)：2回合后+1层；层数可换 pragon(1)/沃尔沃(2)/翻转沃尔沃(4)\n";
    cout << "  炸药第X次使用(至多4)可挡强度<=X-1的攻击(最多挡三雷)\n";
    cout << "- 聂湘：防御(仅挡Bi的防御)攒充能；4点可出一次攻击(不可被吸收)\n";
    cout << "- 田立军：首次0之后每次0.5；对攒清空对方DD；对扇贝外攻击完美防御；遇反弹/吸收/云必败\n";
    cout << "- 张新伟(1局1次)：复制你上一次pragon及以上攻击\n";
    cout << "- 历强(1局1次)：若对手本回合招式与其上一回合完全相同则你直接获胜，否则视为攒\n";
    cout << "===========================================================\n\n";
}

static int readIntInRange(int lo, int hi) {
    while (true) {
        string s;
        if (!std::getline(cin, s)) return lo;
        try {
            int v = std::stoi(s);
            if (v >= lo && v <= hi) return v;
        } catch (...) {
        }
        cout << "输入无效，请输入 " << lo << " ~ " << hi << " 的数字：";
        cout.flush();
    }
}

static void printRoundHeader(int round, const PlayerState& p, const PlayerState& c) {
    cout << "-------------------- 回合 " << round << " --------------------\n";
    cout << "你：DD=" << formatDD(p.dd) << "  雷电=" << p.lightning << "  炸药层=" << p.bombLayers << "  聂湘充能=" << p.nxCharge
         << "  云次数=" << p.cloudUses << "  田立军次数=" << p.tianUses << "\n";
    cout << "电脑：DD=" << formatDD(c.dd) << "  雷电=" << c.lightning << "  炸药层=" << c.bombLayers << "  聂湘充能=" << c.nxCharge
         << "  云次数=" << c.cloudUses << "  田立军次数=" << c.tianUses << "\n";
}

static void printStrategy(const string& title, const vector<Move>& moves, const vector<double>& probs) {
    struct Item { Move m; double p; };
    vector<Item> items;
    items.reserve(moves.size());
    for (size_t i = 0; i < moves.size(); ++i) items.push_back(Item{moves[i], probs[i]});
    std::sort(items.begin(), items.end(), [](const Item& a, const Item& b) { return a.p > b.p; });
    cout << title << "\n";
    cout << std::fixed << std::setprecision(2);
    for (const auto& it : items) {
        cout << "  - " << moveName(it.m) << " : " << (it.p * 100.0) << "%\n";
    }
    cout << std::setprecision(3);
}

static MatrixGameSolution solveGTOWithStatus(const LocalGTO& gto, const PlayerState& p, const PlayerState& c, const string& where) {
    std::ios oldState(nullptr);
    oldState.copyfmt(cout);
    cout << "\n[GTO] 正在求解近似GTO";
    if (!where.empty()) cout << "（" << where << "）";
    cout << "：迭代=" << gto.iterations << "，γ=" << std::fixed << std::setprecision(3) << gto.gamma << "...\n";
    cout.flush();
    MatrixGameSolution sol = gto.solve(p, c);
    cout << "[GTO] 求解完成。\n";
    cout.flush();
    cout.copyfmt(oldState);
    return sol;
}

static void showGTOCurrent(const PlayerState& p, const PlayerState& c, const LocalGTO& gto) {
    MatrixGameSolution sol = solveGTOWithStatus(gto, p, c, "本局面");
    vector<Move> pMoves = listLegalMoves(p, c);
    vector<double> pProbs;
    pProbs.reserve(pMoves.size());
    for (Move m : pMoves) pProbs.push_back(sol.playerStrategy[static_cast<int>(m)]);

    cout << "\n[GTO助手] 当前局面：你DD=" << formatDD(p.dd) << "，电脑DD=" << formatDD(c.dd) << "\n";
    printStrategy("[GTO助手] 你的GTO混合策略（概率%）：", pMoves, pProbs);
    cout << "[GTO助手] 该局面对你（玩家）的估值 V≈" << sol.value << "（+1更有利，-1更不利）\n";
    cout << std::fixed << std::setprecision(2);
    cout << "[GTO助手] 参考胜率≈" << (valueToReferenceWinRate(sol.value) * 100.0) << "%\n\n";
    cout.flush();
}

static bool parseDDUnits(const string& s, int& outUnits) {
    string t = trimCopy(s);
    if (t.empty()) return false;

    int total = 0;
    size_t start = 0;
    while (start < t.size()) {
        size_t plus = t.find('+', start);
        string part = (plus == string::npos) ? t.substr(start) : t.substr(start, plus - start);
        part = trimCopy(part);
        if (part.empty()) return false;

        size_t slash = part.find('/');
        if (slash == string::npos) {
            int whole = 0;
            try { whole = std::stoi(part); } catch (...) { return false; }
            if (whole < 0) return false;
            total += whole * kDDOne;
        } else {
            string aStr = trimCopy(part.substr(0, slash));
            string bStr = trimCopy(part.substr(slash + 1));
            int a = 0, b = 0;
            try { a = std::stoi(aStr); b = std::stoi(bStr); } catch (...) { return false; }
            if (a < 0 || b <= 0) return false;
            if ((a * kDDDen) % b != 0) return false;
            total += (a * kDDDen) / b;
        }

        if (plus == string::npos) break;
        start = plus + 1;
    }

    outUnits = total;
    return true;
}

static bool parseBool(const string& s, bool& out) {
    string t = toLowerCopy(trimCopy(s));
    if (t == "1" || t == "true" || t == "yes" || t == "y") { out = true; return true; }
    if (t == "0" || t == "false" || t == "no" || t == "n") { out = false; return true; }
    return false;
}

static bool parseMoveToken(const string& s, Move& out) {
    string t = toLowerCopy(trimCopy(s));
    if (t == "攒" || t == "charge") { out = Move::Charge; return true; }
    if (t == "bi") { out = Move::Bi; return true; }
    if (t == "防御" || t == "def") { out = Move::Def; return true; }
    if (t == "三雷" || t == "three") { out = Move::Three; return true; }
    if (t == "三雷防" || t == "threedef") { out = Move::ThreeDef; return true; }
    if (t == "大bi" || t == "bigbi") { out = Move::BigBi; return true; }
    if (t == "反弹" || t == "reflect") { out = Move::Reflect; return true; }
    if (t == "自杀" || t == "suicide") { out = Move::Suicide; return true; }
    if (t == "云" || t == "cloud") { out = Move::Cloud; return true; }
    if (t == "炸药" || t == "bomb") { out = Move::Bomb; return true; }
    if (t == "削" || t == "xiao") { out = Move::Xiao; return true; }
    if (t == "pragon") { out = Move::Pragon; return true; }
    if (t == "pragon防" || t == "pragondef") { out = Move::PragonDef; return true; }
    if (t == "沃尔沃" || t == "volvo") { out = Move::Volvo; return true; }
    if (t == "沃尔沃防" || t == "volvodef") { out = Move::VolvoDef; return true; }
    if (t == "旋转三雷" || t == "rotatethree") { out = Move::RotateThree; return true; }
    if (t == "小贝" || t == "xiaobei") { out = Move::XiaoBei; return true; }
    if (t == "翻转沃尔沃" || t == "flipvolvo") { out = Move::FlipVolvo; return true; }
    if (t == "扇贝" || t == "shell") { out = Move::Shell; return true; }
    if (t == "吸收" || t == "absorb") { out = Move::Absorb; return true; }
    if (t == "聂湘" || t == "niexiang") { out = Move::NieXiang; return true; }
    if (t == "聂湘防" || t == "niexiangdef") { out = Move::NieXiangDef; return true; }
    if (t == "距喦" || t == "juyan") { out = Move::JuYan; return true; }
    if (t == "田立军" || t == "tianlijun") { out = Move::TianLiJun; return true; }
    if (t == "张新伟" || t == "zhangxinwei") { out = Move::ZhangXinWei; return true; }
    if (t == "历强" || t == "liqiang") { out = Move::LiQiang; return true; }
    if (t == "pragon(炸药层)" || t == "bombpragon") { out = Move::BombPragon; return true; }
    if (t == "沃尔沃(炸药层)" || t == "bombvolvo") { out = Move::BombVolvo; return true; }
    if (t == "翻转沃尔沃(炸药层)" || t == "bombflipvolvo") { out = Move::BombFlipVolvo; return true; }
    if (t == "三雷(雷电)" || t == "freethree") { out = Move::FreeThree; return true; }
    if (t == "旋转三雷(雷电)" || t == "freerotatethree") { out = Move::FreeRotateThree; return true; }
    return false;
}

static void printGTOQueryHelp() {
    cout << "\n[GTO学习] 输入格式：\n";
    cout << "- 简单：\"玩家DD 电脑DD\"（整数DD，例如：2 3）\n";
    cout << "- 扩展：空格分隔 key=value（玩家用p.，电脑用c. 前缀）\n";
    cout << "\n[GTO学习] 推荐直接复制粘贴的模板：\n";
    cout << "  p.dd=2+1/3 c.dd=3 p.l=0 c.l=0 p.b=0 c.b=0 p.nx=0 c.nx=0 p.cu=0 c.cu=0 p.tu=0 c.tu=0 p.jy=0 c.jy=0\n";
    cout << "  p.dd=1 c.dd=1 p.l=3 c.l=0 p.b=2 c.b=0 p.bp=0,1,0 c.bp=0,0,0 p.last=bi c.last=charge\n";
    cout << "  常用键：\n";
    cout << "    p.dd=2+1/3   c.dd=4   (支持 2, 1/3, 2+1/3)\n";
    cout << "    p.l=3        c.l=0    (雷电层)\n";
    cout << "    p.b=2        c.b=0    (炸药层)\n";
    cout << "    p.bu=1       c.bu=0   (炸药使用次数)\n";
    cout << "    p.bp=0,1,0   c.bp=0,0,0 (炸药延迟到账队列，左到右=本回合末/下回合末/下下回合末)\n";
    cout << "    p.nx=2       c.nx=0   (聂湘充能)\n";
    cout << "    p.cu=1       c.cu=0   (云使用次数)\n";
    cout << "    p.tu=0       c.tu=1   (田立军使用次数，影响0/0.5DD成本)\n";
    cout << "    p.jy=1       c.jy=0   (距喦强化削buff)\n";
    cout << "    p.zxw=1      c.zxw=0  (张新伟是否已用)\n";
    cout << "    p.lq=0       c.lq=1   (历强是否已用)\n";
    cout << "    p.hr=1       p.ha=three (是否有张新伟记录 + 记录的高阶攻击)\n";
    cout << "    p.last=bi    c.last=charge (上一回合出的招，用于历强判断)\n";
    cout << "输入 ? 显示本帮助。\n\n";
    cout.flush();
}

static bool parseStateQuery(const string& line, PlayerState& outP, PlayerState& outC, bool& showHelp) {
    showHelp = false;
    string q = trimCopy(line);
    if (q.empty()) return false;
    if (q == "?" || toLowerCopy(q) == "help") { showHelp = true; return false; }

    {
        std::istringstream iss(q);
        int pdd = -1, cdd = -1;
        if ((iss >> pdd >> cdd) && pdd >= 0 && cdd >= 0) {
            outP = PlayerState{};
            outC = PlayerState{};
            outP.dd = pdd * kDDOne;
            outC.dd = cdd * kDDOne;
            return true;
        }
    }

    outP = PlayerState{};
    outC = PlayerState{};

    std::istringstream iss(q);
    string tok;
    while (iss >> tok) {
        size_t eq = tok.find('=');
        if (eq == string::npos) return false;
        string key = toLowerCopy(trimCopy(tok.substr(0, eq)));
        string val = trimCopy(tok.substr(eq + 1));
        if (key.empty()) return false;

        char side = 0;
        if (key[0] == 'p' || key[0] == 'c') side = key[0];
        else return false;

        string rest = key.substr(1);
        if (!rest.empty() && rest[0] == '.') rest.erase(rest.begin());
        rest.erase(std::remove(rest.begin(), rest.end(), '_'), rest.end());

        PlayerState& target = (side == 'p') ? outP : outC;
        PlayerState& other = (side == 'p') ? outC : outP;
        (void)other;

        if (rest == "dd") {
            int units = 0;
            if (!parseDDUnits(val, units)) return false;
            target.dd = units;
            continue;
        }
        if (rest == "l" || rest == "lightning") {
            int v = 0;
            try { v = std::stoi(val); } catch (...) { return false; }
            target.lightning = clampNonNeg(v);
            continue;
        }
        if (rest == "b" || rest == "bomblayers") {
            int v = 0;
            try { v = std::stoi(val); } catch (...) { return false; }
            target.bombLayers = clampNonNeg(v);
            continue;
        }
        if (rest == "bu" || rest == "bombuses") {
            int v = 0;
            try { v = std::stoi(val); } catch (...) { return false; }
            target.bombUses = clampNonNeg(v);
            continue;
        }
        if (rest == "bp" || rest == "bombpending") {
            int a = 0, b = 0, c = 0;
            char ch1 = 0, ch2 = 0;
            std::istringstream vp(val);
            if (!(vp >> a >> ch1 >> b >> ch2 >> c) || ch1 != ',' || ch2 != ',') return false;
            target.bombPending[0] = clampNonNeg(a);
            target.bombPending[1] = clampNonNeg(b);
            target.bombPending[2] = clampNonNeg(c);
            continue;
        }
        if (rest == "nx" || rest == "nxcharge") {
            int v = 0;
            try { v = std::stoi(val); } catch (...) { return false; }
            target.nxCharge = clampNonNeg(v);
            continue;
        }
        if (rest == "cu" || rest == "clouduses") {
            int v = 0;
            try { v = std::stoi(val); } catch (...) { return false; }
            target.cloudUses = clampNonNeg(v);
            continue;
        }
        if (rest == "tu" || rest == "tianuses") {
            int v = 0;
            try { v = std::stoi(val); } catch (...) { return false; }
            target.tianUses = clampNonNeg(v);
            continue;
        }
        if (rest == "jy" || rest == "juyanbuff") {
            bool b = false;
            if (!parseBool(val, b)) return false;
            target.juyanBuff = b;
            continue;
        }
        if (rest == "zxw" || rest == "zhangused") {
            bool b = false;
            if (!parseBool(val, b)) return false;
            target.zhangUsed = b;
            continue;
        }
        if (rest == "lq" || rest == "liqused") {
            bool b = false;
            if (!parseBool(val, b)) return false;
            target.liqUsed = b;
            continue;
        }
        if (rest == "hr" || rest == "highrecord") {
            bool b = false;
            if (!parseBool(val, b)) return false;
            target.hasHighAttackRecord = b;
            continue;
        }
        if (rest == "ha" || rest == "highattack") {
            Move mv = Move::Charge;
            if (!parseMoveToken(val, mv)) return false;
            target.hasHighAttackRecord = true;
            target.lastHighAttack = mv;
            continue;
        }
        if (rest == "last" || rest == "lastmove") {
            Move mv = Move::Charge;
            if (!parseMoveToken(val, mv)) return false;
            target.lastMove = mv;
            continue;
        }

        return false;
    }

    outP.dd = clampNonNeg(outP.dd);
    outC.dd = clampNonNeg(outC.dd);
    return true;
}

static void showGTOQueryState(const PlayerState& p, const PlayerState& c, const LocalGTO& gto, const string& note) {
    MatrixGameSolution sol = solveGTOWithStatus(gto, p, c, note);

    vector<Move> pMoves = listLegalMoves(p, c);
    vector<Move> cMoves = listLegalMoves(c, p);
    vector<double> pProbs;
    vector<double> cProbs;
    pProbs.reserve(pMoves.size());
    cProbs.reserve(cMoves.size());
    for (Move m : pMoves) pProbs.push_back(sol.playerStrategy[static_cast<int>(m)]);
    for (Move m : cMoves) cProbs.push_back(sol.cpuStrategy[static_cast<int>(m)]);

    cout << "\n[GTO学习] 查询局面：玩家DD=" << formatDD(p.dd) << "，电脑DD=" << formatDD(c.dd) << "\n";
    printStrategy("玩家策略（概率%）：", pMoves, pProbs);
    printStrategy("电脑策略（概率%）：", cMoves, cProbs);
    cout << "[GTO学习] 该局面对玩家的估值 V≈" << sol.value << "\n";
    cout << std::fixed << std::setprecision(2);
    cout << "[GTO学习] 参考胜率≈" << (valueToReferenceWinRate(sol.value) * 100.0) << "%\n\n";
    cout.flush();
}

static void runGTOLearningMode(const LocalGTO& gto) {
    printGTOQueryHelp();
    while (true) {
        cout << "请输入查询（例如：2 3 或 p.dd=2+1/3 c.dd=3 p.l=3）。输入 ? 帮助，q 退出：";
        cout.flush();
        string q;
        if (!std::getline(cin, q)) return;
        q = trimCopy(q);
        if (q.empty()) continue;
        if (toLowerCopy(q) == "q") return;

        PlayerState p, c;
        bool help = false;
        if (!parseStateQuery(q, p, c, help)) {
            if (help) {
                printGTOQueryHelp();
            } else {
                cout << "输入无效（可输入 ? 查看帮助）。\n\n";
            }
            continue;
        }
        showGTOQueryState(p, c, gto, "状态可扩展");
    }
}

static Move readPlayerMove(const PlayerState& p, const PlayerState& c, const LocalGTO& gto, bool gtoToolsEnabled) {
    vector<Move> legal = listLegalMoves(p, c);
    static bool sHelpShown = false;
    while (true) {
        cout << "可选招式：\n";
        for (size_t i = 0; i < legal.size(); ++i) {
            Move m = legal[i];
            PlayerState tmp = p;
            int ddCost = ddCostUnitsForMove(tmp, m);
            string extra;
            if (m == Move::ZhangXinWei && p.hasHighAttackRecord) extra = "（复制:" + moveName(p.lastHighAttack) + "）";
            if (m == Move::Def) extra += "（聂湘充能+1，格挡Bi/削再+1）";
            if (m == Move::JuYan) extra += "（下次削变强化削）";
            if (m == Move::FreeThree) extra += "（消耗3雷电）";
            if (m == Move::FreeRotateThree) extra += "（消耗6雷电）";
            if (m == Move::BombPragon) extra += "（消耗1炸药层）";
            if (m == Move::BombVolvo) extra += "（消耗2炸药层）";
            if (m == Move::BombFlipVolvo) extra += "（消耗4炸药层）";
            if (m == Move::Xiao && p.juyanBuff) extra += "（本次将作为强化削，消耗0DD）";

            cout << "  " << (i + 1) << ". " << moveName(m) << extra << "  [DD消耗=" << formatDD(ddCost) << "]\n";
        }

        if (gtoToolsEnabled) {
            cout << "输入编号出招；g=本局面GTO；s=查询任意DD的GTO；r=重看规则：";
        } else {
            cout << "输入编号出招；r=重看规则：";
        }
        cout.flush();

        string s;
        if (!std::getline(cin, s)) return Move::Charge;
        s = toLowerCopy(trimCopy(s));

        if (s == "r") {
            printRules();
            continue;
        }
        if (gtoToolsEnabled && s == "g") {
            showGTOCurrent(p, c, gto);
            continue;
        }
        if (gtoToolsEnabled && s == "s") {
            if (!sHelpShown) {
                printGTOQueryHelp();
                sHelpShown = true;
            }
            cout << "请输入查询（例如：2 3 或 p.dd=2+1/3 c.dd=3 p.l=3）。输入 ? 帮助，直接回车取消：";
            cout.flush();
            string q;
            if (!std::getline(cin, q)) return Move::Charge;
            q = trimCopy(q);
            if (q.empty()) {
                cout << "\n";
                continue;
            }
            PlayerState qp, qc;
            bool help = false;
            if (!parseStateQuery(q, qp, qc, help)) {
                if (help) printGTOQueryHelp();
                else cout << "输入无效（可输入 ? 查看帮助）。\n\n";
                continue;
            }
            showGTOQueryState(qp, qc, gto, "查询");
            continue;
        }

        try {
            int v = std::stoi(s);
            if (v >= 1 && v <= static_cast<int>(legal.size())) {
                return legal[static_cast<size_t>(v - 1)];
            }
        } catch (...) {
        }
        cout << "输入无效。\n\n";
    }
}

int main() {
    std::ios::sync_with_stdio(false);
    cin.tie(&cout);

#ifdef _WIN32
    // Ensure Windows console uses UTF-8 so Chinese text isn't garbled
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
#endif

    std::mt19937 rng(static_cast<uint32_t>(
        std::chrono::high_resolution_clock::now().time_since_epoch().count()));

    LocalGTO gto;

    cout << "欢迎来到 DD 对战小游戏（新版本）。\n";
    printRules();

    cout << "请选择模式：1=对战Easy  2=对战Hard(近似GTO)  3=GTO学习：";
    cout.flush();
    int mode = readIntInRange(1, 3);

    if (mode == 2 || mode == 3) {
        cout << "请选择近似GTO精度：1=快  2=标准  3=高：";
        cout.flush();
        int prec = readIntInRange(1, 3);
        if (prec == 1) { gto.iterations = 1200; gto.gamma = 0.95; }
        else if (prec == 2) { gto.iterations = 3000; gto.gamma = 0.97; }
        else { gto.iterations = 12000; gto.gamma = 0.985; }
        cout << "GTO参数：迭代=" << gto.iterations << "，γ=" << std::fixed << std::setprecision(3) << gto.gamma << "\n\n";
    }

    if (mode == 3) {
        runGTOLearningMode(gto);
        cout << "按回车退出...";
        cout.flush();
        string dummy;
        std::getline(cin, dummy);
        return 0;
    }

    cout << "是否开启GTO学习/助手功能：1=开启  2=关闭：";
    cout.flush();
    bool gtoToolsEnabled = (readIntInRange(1, 2) == 1);

    if (mode == 1 && gtoToolsEnabled) {
        cout << "请选择近似GTO精度：1=快  2=标准  3=高：";
        cout.flush();
        int prec = readIntInRange(1, 3);
        if (prec == 1) { gto.iterations = 1200; gto.gamma = 0.95; }
        else if (prec == 2) { gto.iterations = 3000; gto.gamma = 0.97; }
        else { gto.iterations = 12000; gto.gamma = 0.985; }
        cout << "GTO参数：迭代=" << gto.iterations << "，γ=" << std::fixed << std::setprecision(3) << gto.gamma << "\n\n";
    }

    PlayerState player;
    PlayerState cpu;
    int round = 1;

    while (true) {
        printRoundHeader(round, player, cpu);

        Move pMove = readPlayerMove(player, cpu, gto, gtoToolsEnabled);

        Move cMove = Move::Charge;
        if (mode == 1) {
            cMove = chooseEasyMove(cpu, player, rng);
        } else {
            MatrixGameSolution sol = gto.solve(player, cpu);
            vector<Move> cMoves = listLegalMoves(cpu, player);
            vector<double> cProbs;
            cProbs.reserve(cMoves.size());
            for (Move m : cMoves) cProbs.push_back(sol.cpuStrategy[static_cast<int>(m)]);
            cMove = sampleFromDist(cMoves, cProbs, rng);
        }

        Action pAct = buildAction(player, cpu, pMove);
        Action cAct = buildAction(cpu, player, cMove);

        cout << "你出招：" << moveName(pMove);
        if (pMove == Move::ZhangXinWei && player.hasHighAttackRecord) cout << "(复制:" << moveName(player.lastHighAttack) << ")";
        cout << "  [DD消耗=" << formatDD(ddCostUnitsForMove(player, pMove)) << "]\n";

        cout << "电脑出招：" << moveName(cMove);
        if (cMove == Move::ZhangXinWei && cpu.hasHighAttackRecord) cout << "(复制:" << moveName(cpu.lastHighAttack) << ")";
        cout << "  [DD消耗=" << formatDD(ddCostUnitsForMove(cpu, cMove)) << "]\n";

        TurnResult tr = simulateTurn(player, cpu, pMove, cMove);
        player = tr.nextP;
        cpu = tr.nextC;

        if (tr.outcome == Outcome::Continue) {
            cout << "结果：未分胜负，进入下一回合。\n\n";
            round += 1;
            continue;
        }

        if (tr.outcome == Outcome::PlayerWin) cout << "结果：你赢了！\n";
        else if (tr.outcome == Outcome::CpuWin) cout << "结果：电脑赢了！\n";
        else cout << "结果：平局！\n";

        cout << "最终：你DD=" << formatDD(player.dd) << "，电脑DD=" << formatDD(cpu.dd) << "\n";
        cout << "按回车退出...";
        cout.flush();
        string dummy;
        std::getline(cin, dummy);
        return 0;
    }
}
