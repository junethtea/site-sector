# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Site Sector Generator
                                 A QGIS plugin
 Generate sectoral site wedges and PCI audits
                             -------------------
        begin                : 2025
        copyright            : (C) 2025 by Jujun Junaedi
        email                : jujun.junaedi@outlook.com
 ***************************************************************************/
"""

def classFactory(iface):
    """Load SiteSector class from file site_sector.
    
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    
    # Import class
    from .site_sector import SiteSector
    return SiteSector(iface)