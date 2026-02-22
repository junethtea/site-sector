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
import math
import os
import re

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRendererCategory,
    QgsSymbol,
    QgsVectorFileWriter,
    QgsVectorLayer
)
from qgis.PyQt.QtCore import Qt, QRect, QUrl, QVariant
from qgis.PyQt.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QIcon,
    QImage,
    QPainter
)
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QProgressDialog


class SiteSector:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.action = QAction(QIcon(icon_path), "Site Sector Generator", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Site Sector", self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&Site Sector", self.action)
            self.iface.removeToolBarIcon(self.action)

    def create_wedge_geom(self, lon, lat, azim, beam, radius_m):
        """Creates a wedge polygon representing a cell sector."""
        radius_deg = radius_m / 111320.0
        points = [QgsPointXY(lon, lat)]
        
        start_angle = azim - (beam / 2)
        end_angle = azim + (beam / 2)
        curr_angle = start_angle
        
        while curr_angle <= end_angle:
            rad = math.radians(90 - curr_angle)
            points.append(
                QgsPointXY(
                    lon + radius_deg * math.cos(rad), 
                    lat + radius_deg * math.sin(rad)
                )
            )
            curr_angle += 3 
            
        points.append(QgsPointXY(lon, lat))
        return QgsGeometry.fromPolygonXY([points])

    def extract_numeric_freq(self, band_string):
        """Extracts the operational frequency from band names (e.g., LTE1800 -> 1800)."""
        nums = re.findall(r'\d+', str(band_string))
        return max(int(n) for n in nums) if nums else 99999

    def run(self):
        from .site_sector_dialog import SiteSectorDialog
        dlg = SiteSectorDialog(self.iface)
        
        if not dlg.exec_():
            return

        inputs = dlg.get_inputs()
        
        # Validate mandatory mappings
        required_cols = [inputs['cols']['lat'], inputs['cols']['lon'], inputs['cols']['azim']]
        if "-- Select Column --" in required_cols:
            QMessageBox.warning(None, "Mapping Error", "Latitude, Longitude, and Azimuth columns are required.")
            return
            
        is_pci_mode = (inputs['active_tab'] == 1)
        
        if is_pci_mode and inputs['cols']['pci'] == "-- Select Column --":
            QMessageBox.warning(None, "PCI Mapping", "Please select the PCI Column in Tab 2.")
            return
            
        if not is_pci_mode and inputs['cols']['band'] == "-- Select Column --":
            QMessageBox.warning(None, "Band Mapping", "Please select the Band/Freq Column in Tab 1.")
            return

        # Prepare dataset and determine unique bands for auto-decrement radius logic
        sorted_bands_list = []
        if inputs['cols']['band'] != "-- Select Column --":
            unique_bands_temp = set()
            try:
                with open(inputs['file_path'], 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if val := row.get(inputs['cols']['band']):
                            unique_bands_temp.add(str(val).strip())
                sorted_bands_list = sorted(list(unique_bands_temp), key=self.extract_numeric_freq)
            except IOError as e:
                QMessageBox.critical(None, "File Error", f"Cannot read input file:\n{e}")
                return

        # Estimate rows for progress dialog
        try:
            with open(inputs['file_path'], 'r', encoding='utf-8-sig') as f:
                total_rows = sum(1 for _ in f) - 1
        except Exception:
            total_rows = 1000 
            
        progress = QProgressDialog("Generating Sectors...", "Cancel", 0, total_rows, self.iface.mainWindow())
        progress.setWindowTitle("Processing Data")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        data_list = []
        all_headers = []
        
        # Process CSV data
        with open(inputs['file_path'], 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            all_headers = reader.fieldnames
            
            for i, row in enumerate(reader):
                if progress.wasCanceled():
                    QMessageBox.information(None, "Cancelled", "Process cancelled by user.")
                    return
                if i % 1000 == 0: 
                    progress.setValue(i)
                    
                try:
                    # Radius processing with overlap decrement handling
                    rad_col = inputs['cols']['radius']
                    if rad_col == "-- Use Manual --":
                        base_rad = inputs['manual']['radius']
                        band_val = str(row.get(inputs['cols']['band'], "")).strip()
                        if band_val in sorted_bands_list:
                            rank = sorted_bands_list.index(band_val)
                            radius = max(base_rad - (rank * 20), 10) 
                        else: 
                            radius = base_rad
                    else: 
                        radius = float(row[rad_col])
                        
                    # Beam processing
                    beam_col = inputs['cols']['beam']
                    beam = inputs['manual']['beam'] if beam_col == "-- Use Manual --" else float(row[beam_col])
                    
                    row_data = dict(row)
                    row_data['_site'] = str(row[inputs['cols']['site']])
                    row_data['_lat'] = float(row[inputs['cols']['lat']])
                    row_data['_lon'] = float(row[inputs['cols']['lon']])
                    row_data['_azim'] = float(row[inputs['cols']['azim']])
                    row_data['_radius'] = radius
                    row_data['_beam'] = beam
                    
                    # Target classification
                    if not is_pci_mode:
                        row_data['_target_val'] = str(row[inputs['cols']['band']]).strip()
                    else:
                        pci_val = float(row[inputs['cols']['pci']])
                        row_data['_target_val'] = str(int(pci_val) % inputs['pci_params']['mod_type'])
                        
                    row_data['_geom'] = self.create_wedge_geom(
                        row_data['_lon'], row_data['_lat'], 
                        row_data['_azim'], row_data['_beam'], row_data['_radius']
                    )
                    data_list.append(row_data)
                    
                except (ValueError, KeyError, TypeError):
                    continue 

        progress.setValue(total_rows)

        if not data_list:
            QMessageBox.warning(None, "Data Error", "No valid sectors could be generated from the dataset.")
            return

        # Sort data for proper rendering stack
        if not is_pci_mode:
            data_list.sort(key=lambda x: self.extract_numeric_freq(x['_target_val']))
        else:
            data_list.sort(key=lambda x: int(x['_target_val']))

        # Initialize vector layer
        layer_name = "Site_Sector_PCI_Audit" if is_pci_mode else "Site_Sector"
        vl = QgsVectorLayer("Polygon?crs=EPSG:4326", layer_name, "memory")
        pr = vl.dataProvider()
        
        fields = QgsFields()
        for h in all_headers: 
            fields.append(QgsField(h, QVariant.String))
        fields.append(QgsField("Gen_Radius", QVariant.Double))
        fields.append(QgsField("Gen_Beam", QVariant.Double))
        
        if is_pci_mode: 
            fields.append(QgsField(f"Mod_{inputs['pci_params']['mod_type']}", QVariant.Int))
            
        pr.addAttributes(fields)
        vl.updateFields()

        # Bulk insert features for performance
        progress.setLabelText("Rendering shapes to map...")
        progress.setValue(0)
        
        features_to_add = []
        for row_data in data_list:
            fet = QgsFeature(fields)
            for h in all_headers: 
                fet.setAttribute(h, str(row_data[h]))
                
            fet.setAttribute("Gen_Radius", row_data['_radius'])
            fet.setAttribute("Gen_Beam", row_data['_beam'])
            
            if is_pci_mode: 
                fet.setAttribute(f"Mod_{inputs['pci_params']['mod_type']}", int(row_data['_target_val']))
                
            fet.setGeometry(row_data['_geom'])
            features_to_add.append(fet)
            
        pr.addFeatures(features_to_add) 
        vl.updateExtents()
        progress.setValue(total_rows)

        # Apply symbology
        categories = []
        unique_targets = sorted(
            list(set(d['_target_val'] for d in data_list)), 
            key=lambda x: self.extract_numeric_freq(x) if not is_pci_mode else int(x)
        )
        opacity_float = (inputs['pci_params']['opacity'] if is_pci_mode else inputs['band_params']['opacity']) / 100.0
        final_colors_map = {} 
        
        for target in unique_targets:
            if not is_pci_mode: 
                col_hex = inputs['band_params']['colors'].get(target, "#888888")
            else:
                idx = int(target)
                col_hex = inputs['pci_params']['colors'][idx] if idx < 6 else "#888888"
            
            final_colors_map[target] = col_hex
            symbol = QgsSymbol.defaultSymbol(vl.geometryType())
            symbol.setColor(QColor(col_hex))
            symbol.setOpacity(opacity_float)
            
            label = f"Mod {target}" if is_pci_mode else str(target)
            categories.append(QgsRendererCategory(target, symbol, label))

        target_field = f"Mod_{inputs['pci_params']['mod_type']}" if is_pci_mode else inputs['cols']['band']
        vl.setRenderer(QgsCategorizedSymbolRenderer(target_field, categories))
        QgsProject.instance().addMapLayer(vl)

        # Export handling
        save_path = inputs['save_path']
        if save_path:
            fmt = inputs['format'].lower()
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.fileEncoding = "UTF-8"
            options.symbologyExport = QgsVectorFileWriter.FeatureSymbology
            
            if "shp" in fmt:
                options.driverName = "ESRI Shapefile" 
                QgsVectorFileWriter.writeAsVectorFormatV2(vl, save_path, QgsProject.instance().transformContext(), options)
                qml_path = save_path.replace(".shp", ".qml")
                vl.saveNamedStyle(qml_path)
                
            elif "tab" in fmt:
                options.driverName = "MapInfo File"   
                QgsVectorFileWriter.writeAsVectorFormatV2(vl, save_path, QgsProject.instance().transformContext(), options)
                
            elif "kml" in fmt:
                self.export_to_kml(data_list, inputs, save_path, all_headers, unique_targets, final_colors_map, is_pci_mode)

            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(save_path)))

        QMessageBox.information(None, "Success", f"Successfully generated {len(data_list)} site sectors.")

    def export_to_kml(self, data, params, output_path, headers, sorted_targets, colors_map, is_pci_mode):
        """Generates a styled KML file with a dynamic floating legend."""
        
        def hex_to_kml_color(hex_str, opacity_pct):
            h = hex_str.lstrip('#')
            r, g, b = h[0:2], h[2:4], h[4:6]
            alpha = f"{int((opacity_pct / 100.0) * 255):02X}"
            return f"{alpha}{b}{g}{r}".lower() 

        def escape_xml(text):
            return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        try:
            output_dir = os.path.dirname(output_path)
            legend_items = sorted_targets[:30] 
            
            # Generate Legend Image
            img_w, img_h = 150, 40 + (len(legend_items) * 25)
            img = QImage(img_w, img_h, QImage.Format_ARGB32)
            img.fill(QColor(255, 255, 255, 220)) 
            
            painter = QPainter(img)
            font = QFont("Arial", 10, QFont.Bold)
            painter.setFont(font)
            painter.setPen(Qt.black)
            
            title = "PCI AUDIT" if is_pci_mode else "LEGEND"
            painter.drawText(QRect(0, 5, img_w, 20), Qt.AlignCenter, title)
            
            font.setBold(False)
            painter.setFont(font)
            y_pos = 30
            
            for t in legend_items:
                hex_col = colors_map.get(t, "#888888")
                painter.setBrush(QBrush(QColor(hex_col)))
                painter.drawRect(10, y_pos, 20, 15)
                lbl_text = f"Mod {t}" if is_pci_mode else str(t)
                painter.drawText(40, y_pos + 12, lbl_text)
                y_pos += 25
            
            painter.end()
            img.save(os.path.join(output_dir, "legend.png"))

            # Generate KML Document
            doc_name = "Site Sector PCI Audit" if is_pci_mode else "Site Sector"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n')
                f.write(f'  <name>{doc_name}</name>\n')
                
                overlay = (
                    '  <ScreenOverlay><name>Legend Overlay</name>'
                    '<Icon><href>legend.png</href></Icon>'
                    '<overlayXY x="0" y="1" xunits="fraction" yunits="fraction"/>'
                    '<screenXY x="0.02" y="0.98" xunits="fraction" yunits="fraction"/>'
                    '<size x="0" y="0" xunits="pixels" yunits="pixels"/></ScreenOverlay>\n'
                )
                f.write(overlay)

                # Collect unique site coordinates for Placemarks
                site_coords = {}
                for row_data in data:
                    site_name = row_data.get(params['cols']['site'], "Unknown")
                    if site_name not in site_coords: 
                        site_coords[site_name] = (row_data['_lon'], row_data['_lat'])
                
                for site, coords in site_coords.items():
                    f.write(
                        f'  <Placemark><name>{escape_xml(site)}</name>'
                        f'<Style><IconStyle><scale>0</scale></IconStyle>'
                        f'<LabelStyle><color>ff00ffff</color><scale>0.8</scale></LabelStyle></Style>'
                        f'<Point><coordinates>{coords[0]},{coords[1]},0</coordinates></Point></Placemark>\n'
                    )

                opacity_val = params['pci_params']['opacity'] if is_pci_mode else params['band_params']['opacity']

                # Build sector polygons
                for row_data in data:
                    hex_col = colors_map.get(row_data['_target_val'], "#888888")
                    kml_col = hex_to_kml_color(hex_col, opacity_val)
                    poly = row_data['_geom'].asPolygon()[0]
                    coord_str = " ".join([f"{pt.x()},{pt.y()},0" for pt in poly])
                    
                    site_name = escape_xml(row_data.get(params["cols"]["site"], "Unknown"))
                    target_lbl = f"Mod_{row_data['_target_val']}" if is_pci_mode else row_data['_target_val']
                    
                    f.write('  <Placemark>\n')
                    f.write(f'    <name>{site_name}_{escape_xml(target_lbl)}</name>\n')
                    f.write('    <ExtendedData>\n')
                    
                    for h in headers:
                        val = escape_xml(row_data.get(h, ""))
                        f.write(f'      <Data name="{escape_xml(h)}"><value>{val}</value></Data>\n')
                        
                    if is_pci_mode:
                        f.write(f'      <Data name="Modulo_Result"><value>{row_data["_target_val"]}</value></Data>\n')
                        
                    f.write('    </ExtendedData>\n')
                    f.write(
                        f'    <Style><LineStyle><color>ff000000</color><width>1</width></LineStyle>'
                        f'<PolyStyle><color>{kml_col}</color></PolyStyle></Style>\n'
                    )
                    f.write(
                        f'    <Polygon><outerBoundaryIs><LinearRing>'
                        f'<coordinates>{coord_str}</coordinates>'
                        f'</LinearRing></outerBoundaryIs></Polygon>\n'
                    )
                    f.write('  </Placemark>\n')

                f.write('</Document>\n</kml>')
                
        except Exception as e:
            QMessageBox.critical(None, "KML Export Error", str(e))