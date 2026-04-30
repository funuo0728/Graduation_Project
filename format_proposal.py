# -*- coding: utf-8 -*-
"""
开题报告格式美化脚本
使用 Word COM 自动化统一文档字体和格式，使文档美观整洁
"""

import os
import sys

try:
    import win32com.client
except ImportError:
    print("请先安装 pywin32: pip install pywin32")
    sys.exit(1)

# 文档路径
DOC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "开题报告.doc")


def format_document():
    """格式化开题报告文档"""
    if not os.path.exists(DOC_PATH):
        print(f"错误：找不到文件 {DOC_PATH}")
        return False

    try:
        # 启动 Word 应用
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False  # 后台运行
        word.DisplayAlerts = 0  # 不显示警告

        # 打开文档（使用绝对路径）
        doc = word.Documents.Open(os.path.abspath(DOC_PATH))

        # ========== 页面设置 ==========
        page_setup = doc.PageSetup
        page_setup.TopMargin = word.CentimetersToPoints(2.54)   # 上边距 2.54cm
        page_setup.BottomMargin = word.CentimetersToPoints(2.54)  # 下边距
        page_setup.LeftMargin = word.CentimetersToPoints(3.17)   # 左边距 3.17cm
        page_setup.RightMargin = word.CentimetersToPoints(3.17)  # 右边距

        # ========== 全文格式 ==========
        # 选中全文
        doc.Content.Select()
        selection = word.Selection

        # 设置正文字体
        selection.Font.Name = "宋体"
        selection.Font.NameFarEast = "宋体"
        selection.Font.Size = 12  # 12磅
        selection.Font.Color = 0  # 黑色

        # 设置段落格式
        selection.ParagraphFormat.Alignment = 0  # 左对齐
        selection.ParagraphFormat.LineSpacingRule = 0  # 单倍行距
        selection.ParagraphFormat.LineSpacing = 18  # 1.5倍行距（12pt * 1.5）
        selection.ParagraphFormat.FirstLineIndent = word.CentimetersToPoints(0.74)  # 首行缩进2字符
        selection.ParagraphFormat.SpaceBefore = 0  # 段前
        selection.ParagraphFormat.SpaceAfter = 0   # 段后

        # ========== 标题格式 ==========
        # 遍历段落，识别标题并应用格式
        for i in range(1, doc.Paragraphs.Count + 1):
            para = doc.Paragraphs(i)
            text = para.Range.Text.strip()

            # 跳过空段落
            if not text:
                continue

            # 判断是否为标题（常见开题报告标题模式）
            # 一级标题：一、二、三 或 第X章
            is_heading1 = (
                any(text.startswith(p) for p in ["一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、", "九、", "十、"]) or
                (text.startswith("第") and "章" in text[:5])
            )

            # 二级标题：1.1 1.2 或 （一）（二）
            is_heading2 = (
                (text[0].isdigit() and "." in text[:4]) or
                text.startswith("（一）") or text.startswith("（二）") or
                text.startswith("(一)") or text.startswith("(二)")
            )

            if is_heading1:
                para.Range.Font.Name = "黑体"
                para.Range.Font.NameFarEast = "黑体"
                para.Range.Font.Size = 14
                para.Range.Font.Bold = True
                para.ParagraphFormat.FirstLineIndent = 0
                para.ParagraphFormat.SpaceBefore = 12
                para.ParagraphFormat.SpaceAfter = 6
                para.ParagraphFormat.Alignment = 0  # 左对齐
            elif is_heading2:
                para.Range.Font.Name = "黑体"
                para.Range.Font.NameFarEast = "黑体"
                para.Range.Font.Size = 12
                para.Range.Font.Bold = True
                para.ParagraphFormat.FirstLineIndent = 0
                para.ParagraphFormat.SpaceBefore = 6
                para.ParagraphFormat.SpaceAfter = 3
                para.ParagraphFormat.Alignment = 0
            else:
                # 正文
                para.Range.Font.Name = "宋体"
                para.Range.Font.NameFarEast = "宋体"
                para.Range.Font.Size = 12
                para.Range.Font.Bold = False
                para.ParagraphFormat.FirstLineIndent = word.CentimetersToPoints(0.74)
                para.ParagraphFormat.LineSpacing = 18

        # 保存并关闭
        doc.Save()
        doc.Close()
        word.Quit()

        print("✓ 格式修改完成！开题报告已更新。")
        return True

    except Exception as e:
        print(f"错误：{e}")
        import traceback
        traceback.print_exc()
        try:
            word.Quit()
        except:
            pass
        return False


if __name__ == "__main__":
    format_document()
