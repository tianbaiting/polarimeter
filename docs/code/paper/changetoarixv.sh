#!/bin/bash
# filepath: c:\workspace\polarizationpaper\changetoarxiv.sh

set -e

WORKDIR="$(pwd)"
ARXIVDIR="$WORKDIR/arxiv"
TEXFILE="polarization.tex"
BIBFILE="ref_tbt.bib"

mkdir -p "$ARXIVDIR"

# 1. 查找所有图片文件名（带扩展名），每行一个
IMGFILES=$(grep -oP '\\includegraphics(\[[^]]*\])?{[^}]+}' "$TEXFILE" | sed 's/.*{//;s/}//')

# 2. 复制图片到 arxiv 目录
echo "$IMGFILES" | sort | uniq | while read -r img; do
    fname=$(basename "$img")
    find "$WORKDIR" -type f -name "$fname" -exec cp -u {} "$ARXIVDIR/" \; 2>/dev/null
done

# 3. 复制 bib 文件
cp "$BIBFILE" "$ARXIVDIR/"

# 4. 复制 tex 文件并替换图片路径为文件名（只保留文件名）
# sed 's/\\includegraphics\(\[[^]]*\]\)*{[^}\/]*\/\([^}]*\)}/\\includegraphic# 
# 4. 用 perl 替换 tex 文件中的图片路径为文件名（只保留文件名）
perl -pe 's|tbt_new_img/|./|g' "$TEXFILE" > "$ARXIVDIR/$TEXFILE"


echo "所有图片和引用文件已复制到 arxiv 文件夹，并修正了 tex 文件中的图片路径。"