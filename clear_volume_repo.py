"""
clear_volume_repo.py
====================
清除 Modal Volume `Faster_Whisper` 中的 /repo 代码缓存。

使用场景
--------
- 更换 REPO_URL（如切换到分叉仓库）后，必须先运行本脚本，
  否则容器 git reset --hard 时 origin 仍指向旧仓库，新代码不会生效。
- 模型权重（/repo/models/）会被一并删除，下次运行将重新下载，
  如需保留模型请使用 --keep-models 选项。

用法
----
    conda activate faster-whisper-modal
    python clear_volume_repo.py                          # 删除整个 /repo（含模型）
    python clear_volume_repo.py --keep-models            # 仅删除代码，保留 /repo/models/
    python clear_volume_repo.py --delete-model custom-model   # 仅删除指定模型子目录
    python clear_volume_repo.py --delete-model custom-model whisper-v3-turbo  # 删除多个
    python clear_volume_repo.py --dry-run                # 仅列出将被删除的内容，不实际删除

注意：`vol.remove_file()` 只能删单个文件，批量删除必须通过 Modal 函数在容器内
      用 shutil.rmtree 操作，本脚本已处理此限制。
"""

import argparse
import sys

import modal

VOLUME_NAME = "Faster_Whisper"
MOUNT_PATH = "/Faster_Whisper"
REPO_PATH = f"{MOUNT_PATH}/repo"

# ── 全局作用域：Modal 要求 @app.function 必须定义在模块顶层 ──────────────────
vol = modal.Volume.from_name(VOLUME_NAME)
app = modal.App("clear-volume-repo")


@app.function(volumes={MOUNT_PATH: vol}, serialized=True)
def _do_delete(keep_models: bool, delete_models: list[str]) -> str:
    """在容器内递归删除 /repo（或仅删除指定部分），并提交 Volume 变更。"""
    import os
    import shutil

    results = []

    if delete_models:
        # 仅删除 /repo/models/ 下的指定子目录
        models_path = os.path.join(REPO_PATH, "models")
        if not os.path.exists(models_path):
            return f"{models_path} 不存在，跳过。"
        for name in delete_models:
            target = os.path.join(models_path, name)
            if os.path.exists(target):
                shutil.rmtree(target)
                results.append(f"  已删除模型目录: {target}")
            else:
                results.append(f"  不存在（跳过）: {target}")

    elif keep_models:
        # 逐项删除 /repo 下除 models/ 以外的所有内容
        if not os.path.exists(REPO_PATH):
            return f"{REPO_PATH} 不存在，跳过。"
        for item in os.listdir(REPO_PATH):
            full = os.path.join(REPO_PATH, item)
            if item == "models":
                results.append(f"  跳过（保留）: {full}")
                continue
            if os.path.isdir(full):
                shutil.rmtree(full)
                results.append(f"  已删除目录: {full}")
            else:
                os.remove(full)
                results.append(f"  已删除文件: {full}")
    else:
        # 删除整个 /repo
        if os.path.exists(REPO_PATH):
            shutil.rmtree(REPO_PATH)
            results.append(f"  已删除: {REPO_PATH}")
        else:
            results.append(f"  {REPO_PATH} 不存在，跳过。")

    vol.commit()  # 持久化变更
    return "\n".join(results) if results else "（无操作）"


# ── 辅助函数 ─────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="清除 Modal Volume 中的 /repo 代码缓存")
    parser.add_argument(
        "--keep-models",
        action="store_true",
        help="保留 /repo/models/ 目录（仅删除代码文件）",
    )
    parser.add_argument(
        "--delete-model",
        metavar="NAME",
        nargs="+",
        dest="delete_models",
        help="仅删除 /repo/models/ 下的指定子目录（可指定多个），不影响代码和其他模型",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅列出将被删除的内容，不实际删除",
    )
    return parser.parse_args()


def list_repo_contents() -> list[str]:
    """列出 /repo 下的顶层条目（用于确认 & dry-run）"""
    try:
        entries = list(vol.listdir("/repo", recursive=False))
        return [e.path for e in entries]
    except Exception:
        return []


def list_model_contents() -> list[str]:
    """列出 /repo/models/ 下的顶层条目"""
    try:
        entries = list(vol.listdir("/repo/models", recursive=False))
        return [e.path for e in entries]
    except Exception:
        return []


# ── 主流程 ───────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    # 互斥检查
    if args.delete_models and args.keep_models:
        print("错误：--delete-model 与 --keep-models 不能同时使用。")
        sys.exit(1)

    print("=== Modal Volume 代码缓存清理工具 ===")
    print(f"Volume : {VOLUME_NAME}")
    print(f"目标路径: {REPO_PATH}")

    if args.delete_models:
        print(f"模式   : 仅删除指定模型子目录：{args.delete_models}")
    elif args.keep_models:
        print("模式   : 保留模型，仅删除代码")
    else:
        print("模式   : 删除整个 /repo（含模型权重）")
    print()

    if args.delete_models:
        # 列出当前 models/ 内容
        model_entries = list_model_contents()
        if not model_entries:
            print("[WARN] /repo/models 目录不存在或已为空，无需清理。")
            sys.exit(0)
        print("/repo/models 顶层内容：")
        for e in model_entries:
            marker = " ← 将删除" if any(e == f"models/{n}" or e.endswith(f"/{n}") or e == n for n in args.delete_models) else ""
            print(f"  {e}{marker}")
        print()
    else:
        # 列出当前 /repo 内容
        entries = list_repo_contents()
        if not entries:
            print("[WARN] /repo 目录不存在或已为空，无需清理。")
            sys.exit(0)
        print("/repo 顶层内容：")
        for e in entries:
            print(f"  {e}")
        print()

    if args.dry_run:
        print("（dry-run 模式，未执行任何删除操作）")
        sys.exit(0)

    # 二次确认
    confirm = input("确认删除？输入 yes 继续，其他任意键取消：").strip().lower()
    if confirm != "yes":
        print("已取消。")
        sys.exit(0)

    print("\n正在启动 Modal 容器执行删除…")
    with app.run():
        output = _do_delete.remote(args.keep_models, args.delete_models or [])

    print(output)

    if args.delete_models:
        print(f"\n[OK] 已删除指定模型目录：{args.delete_models}")
        print("  代码和其他模型未受影响，无需重新 clone 仓库。")
    elif args.keep_models:
        print("\n[OK] 代码已清理，模型权重保留。下次运行 modal_infer.py 时将重新 clone 仓库。")
    else:
        print("\n[OK] 清理完成。下次运行 modal_infer.py 时将重新 clone 仓库。")
        print("  （模型权重也已删除，首次运行会重新下载，耗时较长）")


if __name__ == "__main__":
    main()
