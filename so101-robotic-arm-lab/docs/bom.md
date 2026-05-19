<h1 align="center">Bill of Materials (BOM) & Sourcing</h1>

This page summarizes how to source the **SO-ARM100 / SO-ARM101** hardware, either as ready-made kits or as individual parts for a **leader–follower teleoperation setup**.

> [!NOTE]
> Prices, availability, and vendors change frequently. Treat the values below as *ballpark* references and always check the latest listings.

<br><br>

## 1. Kits

If you don’t want to source every part separately, several vendors sell **SO-ARM100 / SO-ARM101 kits** or compatible bundles.

| Vendor      | Region / Shipping focus                            | Notes |
|------------|-----------------------------------------------------|-------|
| **PartaBot** | 🇺🇸 US                                             | Offers assembled kits and also sells **LeKiwi** and **Koch** robots. |
| **Seeed Studio** | 🌍 International / 🇨🇳 China / 🇯🇵 via Akizuki Denshi / AliExpress | Provides 3D-printed kits and electronics bundles. Good option for global shipping. |
| **WowRobo** | 🌍 International / 🇨🇳 China                        | Sells assembled versions of the arm. |
| **Sudoremove** | 🇰🇷 South Korea                                  | Local supplier for the Korean market. |
| **NeoBot** | 🇨🇳 China                                            | China-based supplier for SO-series arms and accessories. |

Additionally, the **SO-ARM100 follower arm kit (without leader arm)** is available via **Phospho**.  
This is especially useful if you already own a VR headset and only need the physical follower arm.

<br><br>

## 2. Sourcing Parts (Leader + Follower)

For the classic **teleoperation setup** used with the **LeRobot** library:

- The **follower** and **leader** arms share almost all off-the-shelf components (mechanical parts, control boards, clamps, etc.).
- The **main difference is the motor configuration** (gear ratios and sometimes voltage).

If you plan to build a **full two-arm system (leader + follower)**, use the **“Parts for Two Arms”** list below.  
If you only want a **single follower arm**, see the **“Parts for One Follower Arm”** section.

> [!IMPORTANT]
> **Motor voltage & torque**
> - STS3215 servos are available in **7.4 V** and **12 V** versions.  
> - The 7.4 V variant has a stall torque of ~16.5 kg·cm at 6 V (slightly less on 5 V supply).  
> - The 12 V variant reaches ~30 kg·cm stall torque.  
> - We found **7.4 V** sufficient for our setup, but if you want more torque you can switch to **12 V** — and you **must also** upgrade the power supply to **12 V 5 A+**.  
> - For the SO-ARM101, the **leader arm is always 7.4 V.**

<br><br>

## 3. Parts for Two Arms (Leader + Follower)

This BOM covers one **leader** arm and one **follower** arm.

| Part                                            | Qty | Unit cost (US) | Buy (US) | Unit cost (EU) | Buy (EU) | Unit cost (RMB) | Buy (CN) | Unit cost (JPY) | Buy (JP) |
|------------------------------------------------|:---:|---------------:|---------|----------------:|---------|----------------:|---------|----------------:|---------|
| STS3215 Servo 7.4 V, 1:345 gear (C001) **②**   |  7  | $13.89         | Alibaba | €12.20          | Alibaba | ¥97.72          | TaoBao  | ¥2,980          | Akizuki Denshi |
| STS3215 Servo 7.4 V, 1:191 gear (C044) **②**   |  2  | $13.89         | Alibaba | €12.20          | Alibaba | ¥97.72          | –       | ¥2,980          | Akizuki Denshi |
| STS3215 Servo 7.4 V, 1:147 gear (C046) **②**   |  3  | $13.89         | Alibaba | €12.20          | Alibaba | ¥97.72          | –       | ¥2,980          | Akizuki Denshi |
| Motor control board                            |  2  | $10.60         | Amazon  | €11.40          | Amazon  | ¥27             | TaoBao  | ¥980            | Akizuki Denshi |
| USB-C cable (2-pack)                           |  1  | $7.00          | Amazon  | €7.00           | Amazon  | ¥23.9 × 2       | TaoBao  | ¥1,498          | Amazon        |
| Power supply                                   |  2  | $10.00         | Amazon  | €15.70          | Amazon  | ¥22.31          | TaoBao  | ¥1,550          | Akizuki Denshi |
| Table clamp (4-pack)                           |  1  | $9.00          | Amazon  | €9.70           | Amazon  | ¥5.2 × 4        | TaoBao  | ¥2,200          | Amazon        |
| Screwdriver set ¹                              |  1  | $6.00          | Amazon  | €9.00           | Amazon  | ¥14.90          | TaoBao  | ¥500            | Amazon        |
| **Total (approx.)**                            | —   | **$229.88**    | —       | **€226.30**     | —       | **¥1343.16**    | —       | **¥44,530**     | —            |

**Notes**

- ¹ You don’t need this exact screwdriver set, but you **should** have Phillips #0 and #1 tips; these are standard sizes in most small screwdriver kits.
- ² You can buy all six STS3215 servos required for the **SO-ARM101 leader arm** (3 × C046, 2 × C044, 1 × C001) as a **single bundle** on Alibaba. This is often cheaper than buying them separately.

<br><br>

## 4. Parts for One Follower Arm

If you only need a **single follower arm** (no leader arm), use the smaller BOM below.

| Part                                          | Qty | Unit cost (US) | Buy (US) | Unit cost (EU) | Buy (EU) | Unit cost (RMB) | Buy (CN) | Unit cost (JPY) | Buy (JP) |
|----------------------------------------------|:---:|---------------:|---------|----------------:|---------|----------------:|---------|----------------:|---------|
| STS3215 Servo 7.4 V, 1:345 gear (C001)       |  6  | $13.89         | Alibaba | €12.20          | Alibaba | ¥97.72          | TaoBao  | ¥2,980          | Akizuki Denshi |
| Motor control board                          |  1  | $10.60         | Amazon  | €11.40          | Amazon  | ¥27             | TaoBao  | ¥980            | Akizuki Denshi |
| USB-C cable (2-pack)                         |  1  | $7.00          | Amazon  | €7.00           | Amazon  | ¥23.9           | TaoBao  | ¥1,498          | Amazon        |
| Power supply                                 |  1  | $10.00         | Amazon  | €15.70          | Amazon  | ¥22.31          | TaoBao  | ¥1,550          | Akizuki Denshi |
| Table clamp (2-pack)                         |  1  | $5.00          | Amazon  | €8.00           | Amazon  | ¥7.8            | TaoBao  | ¥2,200          | Amazon        |
| Screwdriver set ¹                            |  1  | $6.00          | Amazon  | €9.00           | Amazon  | ¥14.90          | TaoBao  | ¥500            | Amazon        |
| **Total (approx.)**                          | —   | **$121.94**    | —       | **€124.30**     | —       | **¥682.23**     | —       | **¥24,414**     | —            |

Same screwdriver note ¹ applies here as well.

<br><br>

## 5. Optimal way of buying

<p align="center">
    <a href="https://a.co/d/4pNFn4h">
        <img
            src="../assets/images/A3Dparts.png"
            alt="Amazon 3D printed parts"
            width="45%"
            style="border-radius:12px; margin:0 8px;"
        >
    </a>
    <a href="https://a.co/d/8flLPJO">
        <img
            src="../assets/images/aele.png"
            alt="Amazon electronics kit purchase link"
            width="45%"
            style="border-radius:12px; margin:0 8px;"
        >
  </a>
<p>
<br>

## 6. Contributing BOM updates

If you find:

- better local suppliers,
- updated prices,
- or missing links for your country,

please open an issue or submit a PR so we can keep this BOM useful for the rest of the lab and the wider community.
