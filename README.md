# 📡 Site Sector Generator (Global Edition)

**Site Sector Generator** is an advanced, high-performance QGIS plugin designed specifically for Radio Network Optimization (RNO) and Network Performance (NPO) Engineers. It automates the generation of cellular site polygons (wedges) and features a built-in audit engine for LTE PCI Modulo analysis.

Developed by **Jujun Junaedi**.

![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![License](https://img.shields.io/badge/license-GPL--2.0-green.svg)

## 🔥 Key Features

### 1. 🚀 Enterprise-Grade Performance (National Data Ready)
* **Lightning Fast:** Optimized with Bulk Insert rendering to handle National-scale datasets. Generates hundreds of thousands of sectors.

### 2. 🎨 Dynamic Band Styling
* Automatically detects and styles unique frequencies/bands.
rom your raw data using smart Regex parsing (e.g., extracting "1800" from "LTE_1800_MHz").
* **Auto-Decrement Radius:** Intelligently reduces the sector radius for overlapping multi-band layers so every frequency is perfectly visible without manual adjustment.

### 3. 🚨 PCI Modulo Audit Engine
* Instantly visualize LTE interference by generating thematic site sector base on **PCI Modulo 3 (RS Interference)** or **Modulo 6 (PSS Interference)**.

### 4. 🌍 Multi-Format Export with Preserved Thematics
* **ESRI Shapefile (.shp):** Exports geometry and automatically generates a companion `.qml` file to permanently lock your thematic colors.
* **MapInfo (.tab):** Direct native export for MapInfo users.
* **Google Earth (.kml):** Exports 3D-ready KMLs that automatically include an embedded, on-screen floating legend.

## 📸 Screenshots

<img width="411" height="394" alt="ScreenCapture Menu Setting" src="https://github.com/user-attachments/assets/9ce18d46-97de-4cd2-ab84-c14c2283e1a5" />


<img width="616" height="451" alt="ScreenCapture QGIS" src="https://github.com/user-attachments/assets/83edd189-292a-4329-bca7-45310604b11a" />


<img width="742" height="463" alt="ScreenCapture Google Earth" src="https://github.com/user-attachments/assets/be944092-a5f6-4eb1-95f5-e394bc38dcd2" />


## 🛠️ Installation

1. Download the latest release `.zip` file from this repository.
2. Open QGIS.
3. Go to **Plugins** > **Manage and Install Plugins...** > **Install from ZIP**.
4. Select the downloaded `.zip` file and click **Install Plugin**.
5. The **Site Sector Generator** icon will appear in your toolbar.

## 🚀 How to Use

1. Click the plugin icon to open the **Site Sector Generator** dialog.
2. Select your input CSV/Excel data containing Site ID, Latitude, Longitude, and Azimuth.
3. Map the columns accordingly (Radius and Beam can be mapped from columns or use manual fallback values).
4. **Choose your workflow:**
    * **Tab 1 (Style By Band):** Select your Band/Frequency column to generate a standard sectoral map.
    * **Tab 2 (Audit PCI Mode):** Select your PCI column and choose your Modulo target (Mod 3 or Mod 6).
5. Select your desired Export Format, set the Save Path, and click **OK**.

## ☕ Support & Donate

If this tool saves you hours of work, consider buying me a coffee! Your support keeps this project alive and updated.

* **Global:** [Buy Me a Coffee](https://buymeacoffee.com/juneth)
* **Indonesia (OVO / GoPay):** `081510027058`

💡 *Pro Tip: To ensure your colleagues get the latest bug-free version, please share the Official GitHub Link instead of raw ZIP files!*

---

*Dedicated to Taink | Cemot | Bolu | Nara. ❤️❤️❤️❤️*

