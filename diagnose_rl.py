from __future__ import annotations
import os, sys, random
from deidei_env import (
    PlayerState, Move, ALL_MOVES, list_legal_moves, choose_easy_move,
)
try:
    from gui_deidei import MOVE_NAMES_CN
except ImportError:
    MOVE_NAMES_CN = {m: m.name for m in ALL_MOVES}
    MOVE_NAMES_CN[Move.NoMove] = Move.NoMove.name

from rl_ai import model_available, choose_rl_move, rl_strategy_distribution, _load_model
from deidei_gym_env import MOVE_TO_IDX, NUM_MOVES, _legal_mask

LINE = "=" * 78

def mn(m):
    return MOVE_NAMES_CN.get(m, m.name)

def main():
    print(LINE)
    print("【RL AI 诊断工具：判断为什么看起来只会出固定招】")
    print(LINE)

    # 1) 依赖 & 模型加载检查
    print("\n[1/4] 依赖与模型检查")
    print("-" * 40)
    try:
        import torch
        print(f"  torch: OK (v{torch.__version__})  device={'cuda' if torch.cuda.is_available() else 'cpu'}")
    except Exception as e:
        print(f"  torch: 缺失！ {e}")
        print("  -> 请先 pip install torch  (或 -r requirements_rl.txt)")
    try:
        from sb3_contrib import MaskablePPO
        print("  sb3_contrib.MaskablePPO: OK (支持合法动作 mask)")
    except ImportError:
        print("  sb3_contrib: 缺失！会退化为普通 PPO，无动作 mask -> 更容易乱/僵")
        print("  -> pip install sb3-contrib")
    try:
        from stable_baselines3 import PPO
        print("  stable_baselines3: OK")
    except ImportError:
        print("  stable_baselines3: 缺失！无法训练或推理")
        return

    from rl_ai import DEFAULT_CHECKPOINT
    print(f"  模型默认路径: {DEFAULT_CHECKPOINT}")
    print(f"  模型文件存在: {os.path.exists(DEFAULT_CHECKPOINT)}")
    av = model_available()
    print(f"  model_available() = {av}")
    if not av:
        print('  !!! 当前 RL Hard 会 fallback 到 Easy 启发式（所以"出招固定"= Easy 的行为）')
        print("  -> 先运行: python train_ppo_selfplay.py --timesteps 100000 --envs 2")
    else:
        model, has_mask = _load_model()
        print(f"  模型类型: {'MaskablePPO (mask)' if has_mask else '普通 PPO (无mask)'}")
        total_params = sum(p.numel() for p in model.policy.parameters())
        print(f"  策略参数量: {total_params:,}")

    # 2) 同一个局面跑 20 次 choose_rl_move，看出招分布
    print("\n[2/4] 同一开局连跑 30 次 choose_rl_move (stochastic)，看出招分布")
    print("-" * 40)
    rng = random.Random(42)
    p, c = PlayerState(), PlayerState()
    counts = {}
    for _ in range(30):
        m = choose_rl_move(c, p, rng, deterministic=False, fallback_easy=True)
        counts[m] = counts.get(m, 0) + 1
    print(f"  开局状态: 玩家DD=0 电脑DD=0")
    print(f"  30 次采样出招分布:")
    for m, cnt in sorted(counts.items(), key=lambda kv: -kv[1]):
        bar = "#" * int(round(cnt / 30 * 30))
        print(f"    {mn(m):<24s} {cnt:>2d}/30  {bar}")
    if len(counts) == 1:
        print("  !!! 确实是同一个招（30 次全相同）——下一步看策略分布是真单峰还是推理 bug")
    elif len(counts) <= 3:
        print("  -> 仅 2~3 个招有采样，探索性偏弱")

    # 3) 直接打印 RL 策略的概率分布
    print("\n[3/4] 直接读取策略 logits -> 开局完整出招概率（Top-K）")
    print("-" * 40)
    if av:
        legal, probs = rl_strategy_distribution(c, p)
        pairs = sorted(zip(legal, probs), key=lambda x: -x[1])
        print(f"  合法招式 {len(legal)} 个；按 RL 策略概率从高到低：")
        cum = 0.0
        for rank, (m, pr) in enumerate(pairs, 1):
            cum += pr
            bar_len = int(round(pr * 60))
            bar = "#" * bar_len
            print(f"  {rank:>2d}. {mn(m):<24s}  p={pr:>7.2%}  累计={cum:>7.2%}  {bar}")
        # 计算 entropy
        import math
        ent = sum(-x[1] * math.log(x[1] + 1e-12, 2) for x in pairs)
        print(f"  -> 策略熵: {ent:.3f} bits  (合法动作数={len(legal)} 的最大熵={math.log(len(legal),2):.3f})")
        if ent < 0.5:
            print("  !!! 熵太低(<0.5 bit) = 分布几乎是单峰。原因：")
            print("     (a) 训练步数太少，还没学到混合策略")
            print('     (b) 自对弈对手池没在切换，PPO 只学了"如何暴打 Easy"的单一策略')
            print("     (c) entropy coefficient 太低，早期探索性不足")
        elif ent < 1.5:
            print("  -> 熵偏低；训练时间加长 + 提高 ent_coef 会更像 GTO 的混合")
        else:
            print('  -> 熵合理，策略本来就是混合的；只是你采样次数少看起来"固定"')
    else:
        print("  (无模型，跳过策略分布打印)")
        print("  Easy 启发式分布（做对比）：连跑 30 次 choose_easy_move")
        rng2 = random.Random(1)
        cnt_easy = {}
        for _ in range(30):
            m = choose_easy_move(c, p, rng2)
            cnt_easy[m] = cnt_easy.get(m, 0) + 1
        for m, cnt in sorted(cnt_easy.items(), key=lambda kv: -kv[1]):
            print(f"    {mn(m):<24s} {cnt:>2d}/30")
        print("  -> Easy 本身就接近固定招（rng 阈值链），RL fallback 到 Easy 也会像固定招")

    # 4) 不同局面看 RL 是否会换招
    print("\n[4/4] 换 6 种典型局面，看 RL 首选出招是否会变化")
    print("-" * 40)
    scenarios = [
        ("开局 0-0",            PlayerState(),                        PlayerState()),
        ("我方领先 5DD vs 0",   PlayerState(dd=5*6),                  PlayerState(dd=0)),
        ("我方落后 0 vs 5DD",   PlayerState(dd=0),                    PlayerState(dd=5*6)),
        ("炸药 2 层",           PlayerState(bombLayers=2, dd=0),      PlayerState(dd=6)),
        ("雷电 3 层(可免费三雷)", PlayerState(lightning=3, dd=0),     PlayerState(dd=6)),
        ("聂湘 4 充能 + 距喦",  PlayerState(nxCharge=4,juyanBuff=True, dd=6), PlayerState(dd=12)),
    ]
    for name, pp, cc in scenarios:
        if av:
            legal, probs = rl_strategy_distribution(cc, pp)
            if legal and probs:
                best_i = max(range(len(probs)), key=lambda i: probs[i])
                best = legal[best_i]
                best_p = probs[best_i]
                print(f"  {name:<24s} -> RL 选 {mn(best):<22s}  p={best_p:>6.1%}")
            else:
                print(f"  {name:<24s} -> (无合法动作)")
        else:
            rng3 = random.Random(7)
            m = choose_easy_move(cc, pp, rng3)
            print(f"  {name:<24s} -> Easy 选 {mn(m):<22s}  (无 RL 模型，Easy 做参考)")

    print()
    print(LINE)
    print("【结论 & 行动建议】")
    print(LINE)
    print("1. 如果上面 [1/4] 显示 model_available=False  ->  先训练！")
    print("      命令: python train_ppo_selfplay.py --timesteps 150000 --envs 2 --ent-coef 0.06")
    print()
    print("2. 如果 [3/4] 熵<0.5 bit 且 [1/4] 已加载 MaskablePPO  ->  本次补丁会修：")
    print("      (a) ent_coef 0.02 -> 0.06  默认更高探索")
    print("      (b) 对手池切换 Bug（DummyVecEnv 嵌套 wrapper 导致一直打 Easy）已修复")
    print("      (c) latest_ratio 降低，让更多自己的历史版本进入训练")
    print()
    print("3. 如果熵 > 1.5 bits 但 [2/4] 还是只出 1 个招  ->  纯粹是采样次数少，策略本来就是混合的。")
    print()

if __name__ == "__main__":
    main()
