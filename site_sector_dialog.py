#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ==============================================================================
#  PLUGIN      : Site Sector
#  VERSION     : 1.2.0
#  AUTHOR      : Jujun Junaedi
#  EMAIL       : jujun.junaedi@outlook.com
#  COPYRIGHT   : (c) 2025 by Jujun Junaedi
#  LICENSE     : GPL-2.0-or-later
#  DESCRIPTION : Plugin to generate sectoral site wedges and PCI audits.
# ==============================================================================

"""
LICENSE AGREEMENT:
This program is free software; you can redistribute it and/or modify it under 
the terms of the GNU General Public License as published by the Free Software Foundation.
To support the developer and ensure you have the latest stable version, 
please download directly from the Official QGIS Repository.
"""


import csv
import os
import re

from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.gui import QgsCollapsibleGroupBox, QgsColorButton, QgsFileWidget


class SiteSectorDialog(QtWidgets.QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        
        self.setWindowTitle("Site Sector Generator")
        self.setMinimumWidth(550)
        self.resize(550, 500)
        
        self.setup_ui()

    def setup_ui(self):
        """Initializes and arranges all UI components."""
        self.main_layout = QtWidgets.QVBoxLayout(self)
        
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_content = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout(self.scroll_content)

        self._setup_mapping_group()
        self._setup_manual_params_group()
        self._setup_tabbed_interface()
        self._setup_export_group()

        self.layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area) 
        
        self._setup_dialog_buttons() 

        self.update_pci_ui()

    def _setup_mapping_group(self):
        self.group_input = QgsCollapsibleGroupBox("1. General Input & Mapping", self.scroll_content)
        self.input_layout = QtWidgets.QGridLayout(self.group_input)
        
        self.file_widget = QgsFileWidget()
        self.file_widget.fileChanged.connect(self.load_headers)
        
        self.input_layout.addWidget(QtWidgets.QLabel("Select File:"), 0, 0)
        self.input_layout.addWidget(self.file_widget, 0, 1)

        self.combo_site = QtWidgets.QComboBox()
        self.combo_lat = QtWidgets.QComboBox()
        self.combo_lon = QtWidgets.QComboBox()
        self.combo_azim = QtWidgets.QComboBox()
        self.combo_radius = QtWidgets.QComboBox()
        self.combo_beam = QtWidgets.QComboBox()

        self.map_fields = [
            ("Site ID:", self.combo_site, "-- Select Column --"),
            ("Latitude:", self.combo_lat, "-- Select Column --"),
            ("Longitude:", self.combo_lon, "-- Select Column --"),
            ("Azimuth:", self.combo_azim, "-- Select Column --"),
            ("Radius (m):", self.combo_radius, "-- Use Manual --"),
            ("Beam (°):", self.combo_beam, "-- Use Manual --")
        ]

        for i, (label, combo, default_txt) in enumerate(self.map_fields):
            row_idx = i + 1
            self.input_layout.addWidget(QtWidgets.QLabel(label), row_idx, 0)
            self.input_layout.addWidget(combo, row_idx, 1)
            combo.addItem(default_txt)
            
        self.layout.addWidget(self.group_input)

    def _setup_manual_params_group(self):
        self.group_params = QgsCollapsibleGroupBox("Manual Fallback Parameters", self.scroll_content)
        self.params_layout = QtWidgets.QGridLayout(self.group_params)
        
        self.txt_radius = QtWidgets.QLineEdit("200")
        self.txt_beam = QtWidgets.QLineEdit("65")
        
        self.params_layout.addWidget(QtWidgets.QLabel("Base Radius (m):"), 0, 0)
        self.params_layout.addWidget(self.txt_radius, 0, 1)
        self.params_layout.addWidget(QtWidgets.QLabel("Base Beam (°):"), 1, 0)
        self.params_layout.addWidget(self.txt_beam, 1, 1)
        
        self.layout.addWidget(self.group_params)

        self.combo_radius.currentIndexChanged.connect(lambda idx: self.txt_radius.setEnabled(idx == 0))
        self.combo_beam.currentIndexChanged.connect(lambda idx: self.txt_beam.setEnabled(idx == 0))

    def _setup_tabbed_interface(self):
        self.tabs = QtWidgets.QTabWidget()
        self.tab_band = QtWidgets.QWidget()
        self.tab_pci = QtWidgets.QWidget()
        
        self.tabs.addTab(self.tab_band, "1. Style By Band")
        self.tabs.addTab(self.tab_pci, "2. Audit PCI Mode")
        
        self._setup_band_tab()
        self._setup_pci_tab()
        
        self.layout.addWidget(self.tabs)

    def _setup_band_tab(self):
        self.layout_tab_band = QtWidgets.QVBoxLayout(self.tab_band)
        self.band_map_layout = QtWidgets.QHBoxLayout()
        
        self.combo_band = QtWidgets.QComboBox()
        self.combo_band.addItem("-- Select Column --")
        self.combo_band.currentIndexChanged.connect(self.generate_dynamic_bands)
        
        self.band_map_layout.addWidget(QtWidgets.QLabel("Band/Freq Column:"))
        self.band_map_layout.addWidget(self.combo_band)
        self.layout_tab_band.addLayout(self.band_map_layout)

        self.op_band_layout = QtWidgets.QHBoxLayout()
        self.spin_opacity_band = QtWidgets.QSpinBox()
        self.spin_opacity_band.setRange(0, 100)
        self.spin_opacity_band.setValue(50)
        
        self.op_band_layout.addWidget(QtWidgets.QLabel("Opacity (%):")) 
        self.op_band_layout.addWidget(self.spin_opacity_band)
        self.layout_tab_band.addLayout(self.op_band_layout)

        self.color_container = QtWidgets.QWidget()
        self.color_layout = QtWidgets.QGridLayout(self.color_container)
        self.layout_tab_band.addWidget(self.color_container)
        self.layout_tab_band.addStretch()
        
        self.dynamic_color_widgets = {}

    def _setup_pci_tab(self):
        self.layout_tab_pci = QtWidgets.QVBoxLayout(self.tab_pci)
        
        self.pci_map_layout = QtWidgets.QGridLayout()
        self.combo_pci = QtWidgets.QComboBox()
        self.combo_pci.addItem("-- Select Column --")
        
        self.combo_mod = QtWidgets.QComboBox()
        self.combo_mod.addItems(["Mod 3 (RS Interference)", "Mod 6 (PSS Interference)"])
        self.combo_mod.currentIndexChanged.connect(self.update_pci_ui)
        
        self.pci_map_layout.addWidget(QtWidgets.QLabel("PCI Column:"), 0, 0)
        self.pci_map_layout.addWidget(self.combo_pci, 0, 1)
        self.pci_map_layout.addWidget(QtWidgets.QLabel("Audit Mode:"), 1, 0)
        self.pci_map_layout.addWidget(self.combo_mod, 1, 1)
        self.layout_tab_pci.addLayout(self.pci_map_layout)

        self.pci_color_group = QtWidgets.QGroupBox("Modulo Colors & Opacity")
        self.pci_color_layout = QtWidgets.QGridLayout(self.pci_color_group)
        
        self.spin_opacity_pci = QtWidgets.QSpinBox()
        self.spin_opacity_pci.setRange(0, 100)
        self.spin_opacity_pci.setValue(60)
        
        self.pci_color_layout.addWidget(QtWidgets.QLabel("Opacity (%):"), 0, 0)
        self.pci_color_layout.addWidget(self.spin_opacity_pci, 0, 1)

        self.pci_colors = []
        default_pci_colors = [Qt.red, Qt.yellow, Qt.blue, Qt.green, Qt.magenta, Qt.cyan]
        
        for i in range(6):
            btn = QgsColorButton()
            btn.setColor(default_pci_colors[i])
            lbl = QtWidgets.QLabel(f"Mod {i}:")
            
            row, col = (i // 2) + 1, (i % 2) * 2
            self.pci_color_layout.addWidget(lbl, row, col)
            self.pci_color_layout.addWidget(btn, row, col + 1)
            self.pci_colors.append(btn)
            
        self.layout_tab_pci.addWidget(self.pci_color_group)
        self.layout_tab_pci.addStretch()

    def _setup_export_group(self):
        self.group_output = QgsCollapsibleGroupBox("Output Export", self.scroll_content)
        self.out_layout = QtWidgets.QGridLayout(self.group_output)
        
        self.combo_format = QtWidgets.QComboBox()
        self.combo_format.addItems(["ESRI Shapefile (.shp)", "MapInfo (.tab)", "Google Earth (.kml)"])
        self.combo_format.currentIndexChanged.connect(self.update_save_filter)
        
        self.save_widget = QgsFileWidget()
        self.save_widget.setStorageMode(QgsFileWidget.SaveFile)
        self.save_widget.setFilter("Shapefile (*.shp)")
        
        self.out_layout.addWidget(QtWidgets.QLabel("Format:"), 0, 0)
        self.out_layout.addWidget(self.combo_format, 0, 1)
        self.out_layout.addWidget(QtWidgets.QLabel("Save To:"), 1, 0)
        self.out_layout.addWidget(self.save_widget, 1, 1)
        self.layout.addWidget(self.group_output)

    def _setup_dialog_buttons(self):
        self.btn_layout = QtWidgets.QHBoxLayout()
        self.btn_about = QtWidgets.QPushButton("About")
        self.btn_about.clicked.connect(self.show_about)
        
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        self.btn_layout.addWidget(self.btn_about)
        self.btn_layout.addStretch(1)
        self.btn_layout.addWidget(self.button_box)
        self.main_layout.addLayout(self.btn_layout)

    def update_pci_ui(self):
        """Toggles visibility of Modulo color pickers based on selected mode."""
        mod_idx = self.combo_mod.currentIndex()
        for i in range(6):
            btn = self.pci_colors[i]
            lbl_item = self.pci_color_layout.itemAtPosition((i // 2) + 1, (i % 2) * 2)
            if lbl_item and lbl_item.widget():
                show_it = (mod_idx == 0 and i < 3) or (mod_idx == 1 and i < 6)
                btn.setVisible(show_it)
                lbl_item.widget().setVisible(show_it)

    def show_about(self):
        msg = QMessageBox(self.iface.mainWindow())
        msg.setWindowTitle(self.tr("About"))
        msg.setIcon(QMessageBox.Information)
        msg.setTextFormat(Qt.RichText)
        
        about_html = (
            "<h3>Site Sector Generator</h3>"
            "<b>Version:</b> 1.2.0<br>"
            "<b>Author:</b> Jujun Junaedi<br><br>"
            "<b>☕ Support & Donate:</b><br>"
            "If this tool saves you hours of work, consider buying me a coffee!<br>"
            "• <b>Global:</b> Buy Me a Coffee (buymeacoffee.com/juneth)<br>"
            "• <b>Indonesia:</b> OVO / GoPay (081510027058)<br><br>"
            "<div style='background-color: #e8f4f8; padding: 10px; border-radius: 5px; text-align: center; color: #2d98da; border: 1px solid #bdc3c7;'>"
            "<b>💡 PRO TIP FOR SHARING 💡</b><br>"
            "<span style='font-size: 11px;'>"
            "To ensure your colleagues get the latest version without bugs, please share the <b>Official QGIS Plugin Link</b> or <b>GitHub Link</b> instead of raw ZIP files.<br><br>"
            "<i>Biar rekan kerjamu selalu dapat versi terbaru yang bebas error, yuk biasakan share link resmi QGIS/GitHub, bukan bagi-bagi file ZIP mentahan 😉</i>"
            "</span>"
            "</div><br><hr>"
            "<p align='center' style='color: #636e72; font-size: 11px;'>"
            "<i>\"Thanks for Taink | Cemot | Bolu | Nara. ❤️❤️❤️❤️\"</i></p>"
        )
        msg.setText(about_html)
        msg.exec_()

    def update_save_filter(self, idx):
        filters = ["Shapefile (*.shp)", "MapInfo (*.tab)", "Google Earth KML (*.kml)"]
        self.save_widget.setFilter(filters[idx])

    def load_headers(self, path):
        """Reads CSV headers and populates comboboxes without triggering UI updates."""
        if not os.path.exists(path): 
            return
            
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                headers = next(reader)
                
                # Use blockSignals to prevent rendering crashes during bulk updates
                for _, combo, default_txt in self.map_fields:
                    combo.blockSignals(True)
                    combo.clear()
                    combo.addItem(default_txt)
                    combo.addItems(headers)
                    combo.blockSignals(False)
                    
                for combo in [self.combo_band, self.combo_pci]:
                    combo.blockSignals(True)
                    combo.clear()
                    combo.addItem("-- Select Column --")
                    combo.addItems(headers)
                    combo.blockSignals(False)
                    
        except IOError: 
            pass

    def generate_dynamic_bands(self):
        """Dynamically builds color pickers based on unique bands found in the dataset."""
        col_name = self.combo_band.currentText()
        file_path = self.file_widget.filePath()
        
        while self.color_layout.count():
            item = self.color_layout.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
                
        self.dynamic_color_widgets.clear()

        if col_name == "-- Select Column --" or not os.path.exists(file_path): 
            return

        unique_bands = set()
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if val := row.get(col_name):
                        if str(val).strip():
                            unique_bands.add(str(val).strip())
        except IOError: 
            return

        def extract_freq(b):
            nums = re.findall(r'\d+', str(b))
            return max(int(n) for n in nums) if nums else 99999

        sorted_bands = sorted(list(unique_bands), key=extract_freq)
        default_colors = [Qt.red, Qt.green, Qt.blue, Qt.magenta, Qt.cyan, Qt.yellow, Qt.darkGreen, Qt.darkBlue]

        for i, band in enumerate(sorted_bands):
            lbl = QtWidgets.QLabel(f"Band: {band}")
            btn = QgsColorButton()
            btn.setColor(default_colors[i % len(default_colors)])
            
            row, col = i // 2, (i % 2) * 2
            self.color_layout.addWidget(lbl, row, col)
            self.color_layout.addWidget(btn, row, col + 1)
            self.dynamic_color_widgets[band] = btn

    def get_inputs(self):
        """Collects all UI inputs and configurations into a structured dictionary."""
        final_band_colors = {
            band: btn.color().name() 
            for band, btn in self.dynamic_color_widgets.items()
        }
        pci_col_hex = [btn.color().name() for btn in self.pci_colors]

        return {
            "file_path": self.file_widget.filePath(),
            "cols": {
                "site": self.combo_site.currentText(), 
                "lat": self.combo_lat.currentText(),
                "lon": self.combo_lon.currentText(), 
                "azim": self.combo_azim.currentText(),
                "radius": self.combo_radius.currentText(), 
                "beam": self.combo_beam.currentText(),
                "band": self.combo_band.currentText(), 
                "pci": self.combo_pci.currentText()
            },
            "manual": {
                "radius": float(self.txt_radius.text()) if self.txt_radius.text() else 200.0, 
                "beam": float(self.txt_beam.text()) if self.txt_beam.text() else 65.0
            },
            "active_tab": self.tabs.currentIndex(), 
            "band_params": {
                "colors": final_band_colors, 
                "opacity": self.spin_opacity_band.value()
            },
            "pci_params": {
                "mod_type": [3, 6][self.combo_mod.currentIndex()],
                "colors": pci_col_hex,
                "opacity": self.spin_opacity_pci.value()
            },
            "format": self.combo_format.currentText(),
            "save_path": self.save_widget.filePath()
        }