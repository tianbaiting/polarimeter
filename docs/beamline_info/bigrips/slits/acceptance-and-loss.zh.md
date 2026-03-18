# BigRIPS Slits: Large-Angle Particles 与 Momentum Tail

这份说明用于解释 BigRIPS slit 会去掉哪类粒子，以及这件事为什么会同时影响 transmission、beam quality 和 downstream background。

在 RIKEN RIBF 的 BigRIPS fragment separator 中，  
slits（束流限束器）常用于限制束流的 **角度接受度 (angular acceptance)** 和 **动量接受度 (momentum acceptance)**。  

因此会去掉两类粒子：

1. Large-angle particles（大角度粒子）
2. Momentum tail particles（动量尾粒子）

这些概念来自 **束流相空间 (beam phase space)** 的控制，是 fragment separator 的标准操作。

---

## 1 Large-Angle Particles

### 定义

束流粒子并不是完全平行传播，而是具有一定的 **角度分布**：

$$
x'=\frac{dx}{dz}, \qquad y'=\frac{dy}{dz}
$$

多数粒子角度很小，但有一部分粒子偏离较大：

$$
|x'|, |y'| \gg \sigma_{x'}
$$

这些粒子称为 **large-angle particles**。

---

### 来源

可能来源包括：

- beam emittance（束流发射度）
- target scattering（靶散射）
- beam halo（束流晕）
- magnet aberration（磁场像差）

---

### 为什么需要去掉

如果不去掉这些粒子，会导致：

- beam pipe 撞击
- detector background 增加
- spectrometer resolution 下降

因此在 **dispersive focal plane** 上放置 **slits**：

$$
|x| < x_{\text{max}}
$$

从而限制角度接受度。

---

## 2 Momentum Tail

### 定义

束流动量并不完全相同：

$$
p = p_0 + \Delta p
$$

通常呈高斯分布，但会存在 **长尾 (tails)**：

```
  *
    *   *
  *       *
-*---------*-
  p0
```

定义动量偏差：

$$
\delta = \frac{\Delta p}{p}
$$

如果

$$
|\delta| > \text{acceptance}
$$

则称为 **momentum tail particles**。

---

### 来源

- accelerator energy spread  
- nuclear reaction kinematics  
- degrader energy straggling  
- projectile fragmentation  

---

### 在 BigRIPS 中的表现

BigRIPS 是 **磁刚度选择器**：

$$
B\rho = \frac{p}{q}
$$

如果

$$
p \neq p_0
$$

粒子会在 **dispersive focal plane** 偏离：

$$
x = D \cdot \delta
$$

因此 slits 可以切掉：

$$
|\delta| > \delta_{\text{accept}}
$$

这就是 **momentum tail removal**。

---

## 3 BigRIPS 的接受度

BigRIPS 的设计参数：

- horizontal angular acceptance  

$$
\pm 40 \text{ mrad}
$$

- vertical angular acceptance  

$$
\pm 50 \text{ mrad}
$$

- momentum acceptance  

$$
\pm 3\%
$$

这些数值来自 BigRIPS 设计论文。

---

## 4 Slits 的作用

通过在 dispersive focal plane 设置 slits，可以控制：

| 控制量 | 去除对象 |
| ------ | ------ |
| angular acceptance | large-angle particles |
| momentum acceptance | momentum tail |
| spatial halo | beam halo |

实验论文中也指出：

> momentum acceptance was determined using slits

---

## 5 对束流质量的影响

去掉这些粒子后：

| 束流性质 | 变化 |
| --- | --- |
| momentum spread | ↓ |
| angular spread | ↓ |
| background | ↓ |
| particle ID resolution | ↑ |

但代价是束流强度下降：

$$
I_{downstream} < I_{upstream}
$$

---

## 6 关键文献

### BigRIPS 设计论文

T. Kubo et al.

**BigRIPS separator and ZeroDegree spectrometer at RIKEN RI Beam Factory**

Prog. Theor. Exp. Phys. 2012, 03C003

DOI  
https://doi.org/10.1093/ptep/pts064

PDF  
https://pdfs.semanticscholar.org/6937/76e754e93650ec35e5cf728cb9646b7717d0.pdf

---

### BigRIPS 分离与粒子识别

N. Fukuda et al.

**Identification and Separation of Radioactive Isotope Beams by the BigRIPS Separator**

arXiv  
https://arxiv.org/abs/1310.8351

---

### BigRIPS 实验论文示例

JPSJ article

https://journals.jps.jp/doi/10.7566/JPSJ.87.014202

---

## 7 总结

BigRIPS slits 主要去掉两类粒子：

1. **large-angle particles**

$$
|x'|, |y'| \text{ 太大}
$$

2. **momentum tail particles**

$$
|\Delta p/p| \text{ 太大}
$$

这样可以提高束流纯度和分辨率，但会降低束流强度。
