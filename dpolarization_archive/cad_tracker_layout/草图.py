# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     formats: ipynb,py:percent
#     notebook_metadata_filter: kernelspec,language_info,jupytext
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
import matplotlib.pyplot as plt
import numpy as np

# --- 1. 定义参数 ---
center_x = 0
center_y = 0
radius1 = 400
radius2 = 620

# 定义三个点的极坐标
points_polar = {
    'D':  {'r': 400, 'deg': 20.9, 'color': 'green'},
    'P1': {'r': 620, 'deg': 11.2, 'color': 'purple'},
    'P2': {'r': 620, 'deg': 53.4, 'color': 'orange'}
}

# --- 2. 创建画布和坐标系 ---
fig, ax = plt.subplots(figsize=(8, 10))

# --- 3. 创建圆的图形对象 ---
circle1 = plt.Circle((center_x, center_y), radius1, fill=False, color='blue', linestyle=':', label=f'Radius = {radius1}')
circle2 = plt.Circle((center_x, center_y), radius2, fill=False, color='red', linestyle=':', label=f'Radius = {radius2}')

# --- 4. 将圆添加到坐标系中 ---
ax.add_patch(circle1)
ax.add_patch(circle2)

# --- 5. 绘制点和连线 ---
for name, point in points_polar.items():
    # 从字典获取 r 和 角度
    r = point['r']
    angle_deg = point['deg']
    
    # 将角度转换为弧度
    angle_rad = np.deg2rad(angle_deg)
    
    # 将极坐标转换为笛卡尔坐标
    x = r * np.cos(angle_rad)
    y = r * np.sin(angle_rad)
    
    # 绘制点 (使用 scatter)
    # zorder=5 确保点在圆和网格线的上方
    ax.scatter(x, y, color=point['color'], zorder=5, label=f'Point {name} ({r}, {angle_deg}°)')
    
    # 绘制从原点到该点的直线
    ax.plot([center_x, x], [center_y, y], color=point['color'], linestyle='--')


# --- 6. 设置坐标轴范围和样式 ---
limit = radius2 * 1.1
ax.set_xlim(0, limit) 
ax.set_ylim(-limit, limit)
ax.set_aspect('equal', adjustable='box')

# --- 7. 添加网格、标题和图例 ---
plt.grid(True)
plt.title('detector')
plt.xlabel('X ')
plt.ylabel('Y ')
plt.legend() # 显示图例

# --- 8. 显示图形 ---
plt.show()
