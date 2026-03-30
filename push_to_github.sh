#!/bin/bash
# 推送到 GitHub 的輔助腳本

set -e

echo "========================================"
echo "  推送 cuOpt Bug Report 到 GitHub"
echo "========================================"
echo ""

# 檢查是否在 git repo 中
if [ ! -d ".git" ]; then
    echo "錯誤：不在 git repository 中"
    exit 1
fi

# 檢查是否有未提交的變更
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  有未提交的變更，是否先提交？(y/n)"
    read answer
    if [ "$answer" = "y" ]; then
        git add .
        git commit -m "Update before push"
    fi
fi

echo "GitHub Repository 設定"
echo "----------------------"
echo ""
echo "建議的 repo 名稱："
echo "  cuopt-pdlp-infeasibility-bug"
echo ""
echo "步驟："
echo "1. 前往 GitHub 創建新的 public repository"
echo "2. Repository 名稱：cuopt-pdlp-infeasibility-bug"
echo "3. 描述：Minimal reproducible example for cuOpt PDLP false infeasibility bug"
echo "4. 選擇：Public"
echo "5. 不要勾選 'Initialize with README' (我們已經有了)"
echo ""
read -p "已經在 GitHub 創建 repo？(y/n): " created

if [ "$created" != "y" ]; then
    echo ""
    echo "請先到 GitHub 創建 repository，然後重新運行此腳本"
    echo "URL: https://github.com/new"
    exit 0
fi

echo ""
read -p "請輸入你的 GitHub username: " username

if [ -z "$username" ]; then
    echo "錯誤：username 不能為空"
    exit 1
fi

REPO_NAME="cuopt-pdlp-infeasibility-bug"
REPO_URL="https://github.com/$username/$REPO_NAME.git"

echo ""
echo "將推送到："
echo "  $REPO_URL"
echo ""
read -p "確認推送？(y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "取消推送"
    exit 0
fi

# 設定遠端
echo ""
echo "設定 remote..."
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"

# 重命名分支為 main
echo "重命名分支為 main..."
git branch -M main

# 推送
echo "推送到 GitHub..."
git push -u origin main

echo ""
echo "========================================"
echo "✓ 成功推送到 GitHub！"
echo "========================================"
echo ""
echo "Repository URL:"
echo "  https://github.com/$username/$REPO_NAME"
echo ""
echo "接下來："
echo "1. 前往 https://forums.developer.nvidia.com/"
echo "2. 選擇 Acceleration > cuOpt"
echo "3. 創建新主題"
echo "4. 使用 ../ISSUE_BRIEF.md 的內容"
echo "5. 將 [username] 替換為：$username"
echo ""
echo "完成！"
