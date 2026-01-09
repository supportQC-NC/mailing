#!/usr/bin/env python3
"""
KRYSTO - Gestionnaire Clients, Produits, Dépôts-Ventes & Mailing
Version 8.0 - Version Complète avec CRM, Devis/Factures, Statistiques
Devise: XPF (Franc Pacifique)
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image
import sqlite3
import os
from datetime import datetime, timedelta
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import webbrowser
import json
import tempfile
import copy
import urllib.parse
import csv
import shutil
import re
from io import BytesIO

# Pour les graphiques (optionnel)
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Pour les PDF (optionnel - fallback en HTML)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

# ============================================================================
# CONSTANTES
# ============================================================================
COMPANY_NAME = "KRYSTO"
COMPANY_ADDRESS = "Nouméa, Nouvelle-Calédonie"
COMPANY_EMAIL = "contact@krysto.nc"
COMPANY_WEBSITE = "www.krysto.nc"
COMPANY_PHONE = "+687 123 456"
COMPANY_RIDET = ""  # Numéro RIDET entreprise
COMPANY_SLOGAN = "Recyclage & Upcycling"

# TGC Nouvelle-Calédonie (Taxe Générale sur la Consommation)
TGC_RATES = {
    "exonéré": 0,
    "réduit": 3,
    "normal": 11,
    "intermédiaire": 6,
    "spécifique": 22
}
DEFAULT_TGC_RATE = "normal"

# Numérotation factures/devis
INVOICE_PREFIX = "FA"
QUOTE_PREFIX = "DE"

# Types d'interactions CRM
INTERACTION_TYPES = ["📞 Appel", "📧 Email", "🤝 RDV", "💬 Message", "📝 Note", "🎁 Cadeau", "📦 Livraison"]

# Thème de l'application
THEME_MODE = "dark"  # dark ou light

# Couleurs par défaut (peuvent être changées dans l'app)
KRYSTO_PRIMARY = "#6d74ab"
KRYSTO_SECONDARY = "#5cecc8"
KRYSTO_DARK = "#343434"
KRYSTO_LIGHT = "#f5f5f5"

# Fichier de configuration des couleurs
COLORS_CONFIG_FILE = "colors_config.json"

def load_colors_config():
    """Charge les couleurs personnalisées si elles existent."""
    global KRYSTO_PRIMARY, KRYSTO_SECONDARY, KRYSTO_DARK, KRYSTO_LIGHT
    global COMPANY_NAME, COMPANY_ADDRESS, COMPANY_EMAIL, COMPANY_WEBSITE, COMPANY_PHONE, COMPANY_RIDET, COMPANY_SLOGAN
    
    if os.path.exists(COLORS_CONFIG_FILE):
        try:
            with open(COLORS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                KRYSTO_PRIMARY = config.get('primary', KRYSTO_PRIMARY)
                KRYSTO_SECONDARY = config.get('secondary', KRYSTO_SECONDARY)
                KRYSTO_DARK = config.get('dark', KRYSTO_DARK)
                KRYSTO_LIGHT = config.get('light', KRYSTO_LIGHT)
                COMPANY_NAME = config.get('company_name', COMPANY_NAME)
                COMPANY_ADDRESS = config.get('company_address', COMPANY_ADDRESS)
                COMPANY_EMAIL = config.get('company_email', COMPANY_EMAIL)
                COMPANY_WEBSITE = config.get('company_website', COMPANY_WEBSITE)
                COMPANY_PHONE = config.get('company_phone', COMPANY_PHONE)
                COMPANY_RIDET = config.get('company_ridet', COMPANY_RIDET)
                COMPANY_SLOGAN = config.get('company_slogan', COMPANY_SLOGAN)
        except: pass

def save_colors_config():
    """Sauvegarde la configuration des couleurs."""
    config = {
        'primary': KRYSTO_PRIMARY,
        'secondary': KRYSTO_SECONDARY,
        'dark': KRYSTO_DARK,
        'light': KRYSTO_LIGHT,
        'company_name': COMPANY_NAME,
        'company_address': COMPANY_ADDRESS,
        'company_email': COMPANY_EMAIL,
        'company_website': COMPANY_WEBSITE,
        'company_phone': COMPANY_PHONE,
        'company_ridet': COMPANY_RIDET,
        'company_slogan': COMPANY_SLOGAN,
    }
    with open(COLORS_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# Charger les couleurs au démarrage
load_colors_config()

SMTP_CONFIG_FILE = "smtp_config.json"
DB_PATH = "krysto_workshop.db"
CURRENCY = "XPF"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def load_smtp_config():
    default = {"host": "smtp.hostinger.com", "port": 465, "use_ssl": True,
               "username": "contact@krysto.io", "password": "", "from_name": "KRYSTO"}
    if os.path.exists(SMTP_CONFIG_FILE):
        try:
            with open(SMTP_CONFIG_FILE, 'r') as f:
                return {**default, **json.load(f)}
        except: pass
    return default


def get_smtp_config():
    """Retourne la config SMTP avec les clés normalisées."""
    config = load_smtp_config()
    return {
        'smtp_host': config.get('host', ''),
        'smtp_port': config.get('port', 465),
        'smtp_user': config.get('username', ''),
        'smtp_password': config.get('password', ''),
        'smtp_from_name': config.get('from_name', 'KRYSTO'),
        'use_ssl': config.get('use_ssl', True)
    }


def save_smtp_config(config):
    try:
        with open(SMTP_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except: return False

def format_price(amount):
    return f"{amount:,.0f} {CURRENCY}"

# ============================================================================
# BLOCS EMAIL
# ============================================================================
class EmailBlock:
    BLOCK_TYPE = "base"
    BLOCK_ICON = "📦"
    BLOCK_NAME = "Bloc"
    
    def __init__(self, content=None):
        self.content = content or self.get_default_content()
        self.id = f"block_{datetime.now().strftime('%H%M%S%f')}"
    
    @classmethod
    def get_default_content(cls): return {}
    def to_html(self, context=None): return ""
    def get_preview_text(self): return f"{self.BLOCK_ICON} {self.BLOCK_NAME}"
    def clone(self): return self.__class__(copy.deepcopy(self.content))


class TextBlock(EmailBlock):
    BLOCK_TYPE = "text"
    BLOCK_ICON = "📝"
    BLOCK_NAME = "Texte"
    
    @classmethod
    def get_default_content(cls):
        return {"text": "", "font_size": 15, "font_family": "Segoe UI, sans-serif",
                "color": KRYSTO_DARK, "background": "transparent", "bold": False,
                "italic": False, "underline": False, "align": "left", "line_height": 1.8,
                "padding": {"top": 10, "right": 0, "bottom": 10, "left": 0},
                "margin": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "border_radius": 0}
    
    def to_html(self, context=None):
        c = self.content
        padding_dict = c.get('padding', {"top": 10, "right": 0, "bottom": 10, "left": 0})
        padding = f"{padding_dict.get('top', 10)}px {padding_dict.get('right', 0)}px {padding_dict.get('bottom', 10)}px {padding_dict.get('left', 0)}px"
        font_size = c.get('font_size', 15)
        font_family = c.get('font_family', 'Segoe UI, sans-serif')
        color = c.get('color', KRYSTO_DARK)
        background = c.get('background', 'transparent')
        line_height = c.get('line_height', 1.8)
        align = c.get('align', 'left')
        border_radius = c.get('border_radius', 0)
        text = c.get('text', '')
        
        style = f"font-size:{font_size}px;font-family:{font_family};color:{color};background-color:{background};line-height:{line_height};text-align:{align};padding:{padding};border-radius:{border_radius}px;"
        if c.get('bold'): style += "font-weight:bold;"
        if c.get('italic'): style += "font-style:italic;"
        if c.get('underline'): style += "text-decoration:underline;"
        return f'<div style="{style}">{text.replace(chr(10), "<br>")}</div>'
    
    def get_preview_text(self):
        t = self.content.get('text', '')[:50]
        return f"📝 {t}..." if len(self.content.get('text', '')) > 50 else f"📝 {t or 'Texte vide'}"


class TitleBlock(EmailBlock):
    BLOCK_TYPE = "title"
    BLOCK_ICON = "📌"
    BLOCK_NAME = "Titre"
    
    @classmethod
    def get_default_content(cls):
        return {"text": "", "level": "h2", "font_size": 24, "font_family": "Segoe UI, sans-serif",
                "color": KRYSTO_DARK, "align": "left", "underline_style": "gradient",
                "underline_color": KRYSTO_SECONDARY, "underline_height": 3, "margin_bottom": 20}
    
    def to_html(self, context=None):
        c = self.content
        text = c.get('text', '')
        level = c.get('level', 'h2')
        font_size = c.get('font_size', 24)
        font_family = c.get('font_family', 'Segoe UI, sans-serif')
        color = c.get('color', KRYSTO_DARK)
        align = c.get('align', 'left')
        underline_style = c.get('underline_style', 'gradient')
        underline_color = c.get('underline_color', KRYSTO_SECONDARY)
        underline_height = c.get('underline_height', 3)
        margin_bottom = c.get('margin_bottom', 20)
        
        underline = ""
        if underline_style == "gradient":
            underline = f'<div style="height:{underline_height}px;background:linear-gradient(90deg,{KRYSTO_SECONDARY},{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});margin-top:10px;border-radius:2px;"></div>'
        elif underline_style == "solid":
            underline = f'<div style="height:{underline_height}px;background-color:{underline_color};margin-top:10px;"></div>'
        return f'<{level} style="margin:0 0 {margin_bottom}px 0;color:{color};font-size:{font_size}px;font-family:{font_family};text-align:{align};">{text}{underline}</{level}>'
    
    def get_preview_text(self):
        return f"📌 {self.content.get('text', '') or 'Titre vide'}"


class ImageBlock(EmailBlock):
    BLOCK_TYPE = "image"
    BLOCK_ICON = "🖼️"
    BLOCK_NAME = "Image"
    
    @classmethod
    def get_default_content(cls):
        return {"url": "", "alt": "Image", "width": "100%", "max_width": "100%", "height": "auto",
                "align": "center", "border_radius": 12, "shadow": True, "caption": "",
                "caption_color": "#666666", "link_url": "", "padding": 10}
    
    def to_html(self, context=None):
        c = self.content
        url = c.get('url', '')
        if not url: return ""
        
        alt = c.get('alt', 'Image')
        width = c.get('width', '100%')
        max_width = c.get('max_width', '100%')
        height = c.get('height', 'auto')
        align = c.get('align', 'center')
        border_radius = c.get('border_radius', 12)
        shadow_enabled = c.get('shadow', True)
        caption = c.get('caption', '')
        caption_color = c.get('caption_color', '#666666')
        link_url = c.get('link_url', '')
        padding = c.get('padding', 10)
        
        shadow = "box-shadow:0 4px 15px rgba(0,0,0,0.1);" if shadow_enabled else ""
        img_style = f"max-width:{max_width};width:{width};height:{height};border-radius:{border_radius}px;{shadow}"
        img_html = f'<img src="{url}" alt="{alt}" style="{img_style}">'
        if link_url: img_html = f'<a href="{link_url}" target="_blank">{img_html}</a>'
        caption_html = f'<p style="margin:10px 0 0 0;color:{caption_color};font-size:12px;text-align:center;">{caption}</p>' if caption else ""
        return f'<div style="text-align:{align};padding:{padding}px;">{img_html}{caption_html}</div>'
    
    def get_preview_text(self):
        url = self.content.get('url', '')
        return f"🖼️ {url[:40]}..." if len(url) > 40 else f"🖼️ {url or 'Aucune image'}"


class ButtonBlock(EmailBlock):
    BLOCK_TYPE = "button"
    BLOCK_ICON = "🔘"
    BLOCK_NAME = "Bouton"
    
    @classmethod
    def get_default_content(cls):
        return {"text": "Cliquez ici", "url": f"https://{COMPANY_WEBSITE}", "style": "gradient",
                "bg_color": KRYSTO_PRIMARY, "bg_color_2": KRYSTO_SECONDARY, "text_color": "#ffffff",
                "border_color": KRYSTO_PRIMARY, "font_size": 15, "padding_x": 40, "padding_y": 14,
                "border_radius": 25, "shadow": True, "icon": "", "icon_position": "left",
                "full_width": False, "align": "center"}
    
    def to_html(self, context=None):
        c = self.content
        text = c.get('text', 'Cliquez ici')
        url = c.get('url', f"https://{COMPANY_WEBSITE}")
        style = c.get('style', 'gradient')
        bg_color = c.get('bg_color', KRYSTO_PRIMARY)
        bg_color_2 = c.get('bg_color_2', KRYSTO_SECONDARY)
        text_color = c.get('text_color', '#ffffff')
        border_color = c.get('border_color', KRYSTO_PRIMARY)
        font_size = c.get('font_size', 15)
        padding_x = c.get('padding_x', 40)
        padding_y = c.get('padding_y', 14)
        border_radius = c.get('border_radius', 25)
        shadow_enabled = c.get('shadow', True)
        icon = c.get('icon', '')
        icon_position = c.get('icon_position', 'left')
        full_width = c.get('full_width', False)
        align = c.get('align', 'center')
        
        shadow = "box-shadow:0 4px 15px rgba(109,116,171,0.4);" if shadow_enabled else ""
        if style == "gradient":
            bg_style = f"background:linear-gradient(135deg,{bg_color} 0%,{bg_color_2} 100%);"
            border_style = "border:none;"
        elif style == "outline":
            bg_style = "background-color:transparent;"
            border_style = f"border:2px solid {border_color};"
        else:
            bg_style = f"background-color:{bg_color};"
            border_style = "border:none;"
        width_style = "display:block;width:100%;" if full_width else "display:inline-block;"
        icon_html = f'<span style="margin-{"right" if icon_position=="left" else "left"}:8px;">{icon}</span>' if icon else ""
        text_content = f'{icon_html}{text}' if icon_position == "left" else f'{text}{icon_html}'
        return f'''<div style="text-align:{align};padding:10px 0;"><a href="{url}" style="{width_style}padding:{padding_y}px {padding_x}px;{bg_style}{border_style}color:{text_color};text-decoration:none;border-radius:{border_radius}px;font-weight:bold;font-size:{font_size}px;{shadow}text-align:center;">{text_content}</a></div>'''
    
    def get_preview_text(self):
        return f"🔘 {self.content.get('text', 'Bouton')}"


class DividerBlock(EmailBlock):
    BLOCK_TYPE = "divider"
    BLOCK_ICON = "➖"
    BLOCK_NAME = "Séparateur"
    
    @classmethod
    def get_default_content(cls):
        return {"style": "gradient", "color": KRYSTO_SECONDARY, "color_2": KRYSTO_PRIMARY,
                "height": 3, "width": "100%", "align": "center", "margin_top": 20,
                "margin_bottom": 20, "border_radius": 2}
    
    def to_html(self, context=None):
        c = self.content
        style = c.get('style', 'gradient')
        color = c.get('color', KRYSTO_SECONDARY)
        color_2 = c.get('color_2', KRYSTO_PRIMARY)
        height = c.get('height', 3)
        width = c.get('width', '100%')
        margin_top = c.get('margin_top', 20)
        margin_bottom = c.get('margin_bottom', 20)
        border_radius = c.get('border_radius', 2)
        
        margin = f"margin:{margin_top}px auto {margin_bottom}px;"
        if style == "gradient":
            return f'<div style="{margin}width:{width};height:{height}px;background:linear-gradient(90deg,{color},{color_2},{color});border-radius:{border_radius}px;"></div>'
        elif style == "solid":
            return f'<div style="{margin}width:{width};height:{height}px;background-color:{color};border-radius:{border_radius}px;"></div>'
        elif style in ("dashed", "dotted"):
            return f'<hr style="{margin}width:{width};border:none;border-top:{height}px {style} {color};">'
        return f'<div style="{margin}height:{height}px;"></div>'
    
    def get_preview_text(self):
        return f"➖ {self.content.get('style', 'gradient').capitalize()}"


class SpacerBlock(EmailBlock):
    BLOCK_TYPE = "spacer"
    BLOCK_ICON = "📏"
    BLOCK_NAME = "Espace"
    
    @classmethod
    def get_default_content(cls): return {"height": 30}
    def to_html(self, context=None): return f'<div style="height:{self.content.get("height", 30)}px;"></div>'
    def get_preview_text(self): return f"📏 {self.content.get('height', 30)}px"


class QuoteBlock(EmailBlock):
    BLOCK_TYPE = "quote"
    BLOCK_ICON = "💬"
    BLOCK_NAME = "Citation"
    
    @classmethod
    def get_default_content(cls):
        return {"text": "", "author": "", "style": "modern", "accent_color": KRYSTO_PRIMARY,
                "bg_color": "#f8f9fa", "text_color": KRYSTO_DARK, "font_size": 16,
                "font_style": "italic", "padding": 25, "border_radius": 12}
    
    def to_html(self, context=None):
        c = self.content
        text = c.get('text', '')
        author_name = c.get('author', '')
        style = c.get('style', 'modern')
        accent_color = c.get('accent_color', KRYSTO_PRIMARY)
        bg_color = c.get('bg_color', '#f8f9fa')
        text_color = c.get('text_color', KRYSTO_DARK)
        font_size = c.get('font_size', 16)
        font_style = c.get('font_style', 'italic')
        padding = c.get('padding', 25)
        border_radius = c.get('border_radius', 12)
        
        author = f'<p style="margin:15px 0 0 0;font-size:13px;color:{accent_color};font-style:normal;">— {author_name}</p>' if author_name else ""
        if style == "modern":
            return f'''<div style="background-color:{bg_color};padding:{padding}px;border-left:4px solid {accent_color};border-radius:0 {border_radius}px {border_radius}px 0;margin:15px 0;"><p style="margin:0;font-size:{font_size}px;color:{text_color};font-style:{font_style};line-height:1.6;">"{text}"</p>{author}</div>'''
        return f'''<div style="padding:{padding}px 0;margin:15px 0;border-top:1px solid #ddd;border-bottom:1px solid #ddd;"><p style="margin:0;font-size:{font_size}px;color:{text_color};font-style:{font_style};">"{text}"</p>{author}</div>'''
    
    def get_preview_text(self):
        t = self.content.get('text', '')[:40]
        return f"💬 {t}..." if len(self.content.get('text', '')) > 40 else f"💬 {t or 'Citation vide'}"


class ListBlock(EmailBlock):
    BLOCK_TYPE = "list"
    BLOCK_ICON = "📋"
    BLOCK_NAME = "Liste"
    
    @classmethod
    def get_default_content(cls):
        return {"items": [], "style": "icons", "default_icon": "✓", "icon_color": KRYSTO_SECONDARY,
                "text_color": KRYSTO_DARK, "font_size": 14, "spacing": 12, "icon_size": 18}
    
    def to_html(self, context=None):
        c = self.content
        items = c.get('items', [])
        if not items: return ""
        
        style = c.get('style', 'icons')
        default_icon = c.get('default_icon', '✓')
        icon_color = c.get('icon_color', KRYSTO_SECONDARY)
        text_color = c.get('text_color', KRYSTO_DARK)
        font_size = c.get('font_size', 14)
        spacing = c.get('spacing', 12)
        icon_size = c.get('icon_size', 18)
        
        items_html = ""
        for i, item in enumerate(items):
            item_text = item.get('text', '')
            item_icon = item.get('icon', default_icon)
            
            if style == "numbers": icon = f'<span style="color:{icon_color};font-weight:bold;margin-right:10px;">{i+1}.</span>'
            elif style == "bullets": icon = f'<span style="color:{icon_color};margin-right:10px;">•</span>'
            elif style == "check": icon = f'<span style="color:{icon_color};margin-right:10px;font-size:{icon_size}px;">✓</span>'
            else: icon = f'<span style="color:{icon_color};margin-right:10px;font-size:{icon_size}px;">{item_icon}</span>'
            items_html += f'<div style="display:flex;align-items:flex-start;margin-bottom:{spacing}px;">{icon}<span style="color:{text_color};font-size:{font_size}px;line-height:1.5;">{item_text}</span></div>'
        return f'<div style="padding:10px 0;">{items_html}</div>'
    
    def get_preview_text(self):
        return f"📋 Liste: {len(self.content.get('items', []))} élément(s)"


class PromoCodeBlock(EmailBlock):
    BLOCK_TYPE = "promo_code"
    BLOCK_ICON = "🎁"
    BLOCK_NAME = "Code Promo"
    
    @classmethod
    def get_default_content(cls):
        return {"code": "KRYSTO20", "description": "Profitez de -20% sur votre commande",
                "expiry": "", "style": "card", "gradient_start": KRYSTO_PRIMARY,
                "gradient_end": KRYSTO_SECONDARY, "text_color": "#ffffff"}
    
    def to_html(self, context=None):
        c = self.content
        code = c.get('code', 'KRYSTO20')
        description = c.get('description', '')
        expiry_date = c.get('expiry', '')
        style = c.get('style', 'card')
        gradient_start = c.get('gradient_start', KRYSTO_PRIMARY)
        gradient_end = c.get('gradient_end', KRYSTO_SECONDARY)
        text_color = c.get('text_color', '#ffffff')
        
        expiry = f'<p style="margin:15px 0 0 0;color:#ff6b6b;font-size:13px;font-weight:bold;">⏰ Valable jusqu\'au {expiry_date}</p>' if expiry_date else ""
        if style == "card":
            return f'''<div style="text-align:center;padding:30px;background:linear-gradient(135deg,{gradient_start},{gradient_end});border-radius:15px;margin:20px 0;"><p style="margin:0 0 15px 0;color:rgba(255,255,255,0.9);font-size:14px;">{description}</p><div style="background:rgba(255,255,255,0.2);display:inline-block;padding:15px 40px;border-radius:10px;border:2px dashed rgba(255,255,255,0.5);"><span style="color:{text_color};font-size:28px;font-weight:bold;letter-spacing:4px;">{code}</span></div>{expiry}</div>'''
        return f'''<div style="text-align:center;padding:15px;"><p style="margin:0 0 10px 0;color:#666;">{description}</p><span style="font-size:24px;font-weight:bold;color:{gradient_start};letter-spacing:3px;">{code}</span></div>'''
    
    def get_preview_text(self):
        return f"🎁 {self.content.get('code', 'PROMO')}"


# Définition des réseaux sociaux avec vraies icônes (URL CDN)
SOCIAL_NETWORKS = {
    "facebook": {
        "name": "Facebook",
        "color": "#1877F2",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/facebook.svg",
        "placeholder": "https://facebook.com/votrepage"
    },
    "instagram": {
        "name": "Instagram", 
        "color": "#E4405F",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/instagram.svg",
        "placeholder": "https://instagram.com/votrepage"
    },
    "tiktok": {
        "name": "TikTok",
        "color": "#000000",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/tiktok.svg",
        "placeholder": "https://tiktok.com/@votrepage"
    },
    "youtube": {
        "name": "YouTube",
        "color": "#FF0000",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/youtube.svg",
        "placeholder": "https://youtube.com/c/votrepage"
    },
    "linkedin": {
        "name": "LinkedIn",
        "color": "#0A66C2",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/linkedin.svg",
        "placeholder": "https://linkedin.com/company/votrepage"
    },
    "twitter": {
        "name": "X (Twitter)",
        "color": "#000000",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/x.svg",
        "placeholder": "https://x.com/votrepage"
    },
    "pinterest": {
        "name": "Pinterest",
        "color": "#BD081C",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/pinterest.svg",
        "placeholder": "https://pinterest.com/votrepage"
    },
    "whatsapp": {
        "name": "WhatsApp",
        "color": "#25D366",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/whatsapp.svg",
        "placeholder": "https://wa.me/687123456"
    },
    "messenger": {
        "name": "Messenger",
        "color": "#00B2FF",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/messenger.svg",
        "placeholder": "https://m.me/votrepage"
    },
    "snapchat": {
        "name": "Snapchat",
        "color": "#FFFC00",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/snapchat.svg",
        "placeholder": "https://snapchat.com/add/votrepage"
    },
    "telegram": {
        "name": "Telegram",
        "color": "#26A5E4",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/telegram.svg",
        "placeholder": "https://t.me/votrepage"
    },
    "website": {
        "name": "Site Web",
        "color": "#4A90D9",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/googlechrome.svg",
        "placeholder": "https://votresite.com"
    },
    "email": {
        "name": "Email",
        "color": "#EA4335",
        "icon_url": "https://cdn.jsdelivr.net/npm/simple-icons@v9/icons/gmail.svg",
        "placeholder": "mailto:contact@votresite.com"
    },
}


class SocialBlock(EmailBlock):
    BLOCK_TYPE = "social"
    BLOCK_ICON = "🔗"
    BLOCK_NAME = "Réseaux sociaux"
    
    @classmethod
    def get_default_content(cls):
        # Par défaut, tous les réseaux sont disponibles mais sans URL
        networks = {key: "" for key in SOCIAL_NETWORKS.keys()}
        return {
            "networks": networks,
            "style": "colored",  # colored, mono, outline
            "size": 40,
            "gap": 12,
            "align": "center",
            "border_radius": 50,  # % pour cercle
            "mono_color": "#666666"  # couleur pour style mono
        }
    
    def to_html(self, context=None):
        c = self.content
        networks = c.get('networks', {})
        style = c.get('style', 'colored')
        size = c.get('size', 40)
        gap = c.get('gap', 12)
        align = c.get('align', 'center')
        border_radius = c.get('border_radius', 50)
        mono_color = c.get('mono_color', '#666666')
        
        # Filtrer les réseaux avec URL
        active_networks = [(key, url) for key, url in networks.items() if url and key in SOCIAL_NETWORKS]
        if not active_networks:
            return ""
        
        # Lettres/symboles pour chaque réseau (fallback compatible email)
        network_letters = {
            "facebook": "f", "instagram": "📷", "tiktok": "T", "youtube": "▶",
            "linkedin": "in", "twitter": "𝕏", "pinterest": "P", "whatsapp": "💬",
            "messenger": "💬", "snapchat": "👻", "telegram": "✈", "website": "🌐", "email": "✉"
        }
        
        icons_html = ""
        for net_key, url in active_networks:
            net_info = SOCIAL_NETWORKS[net_key]
            color = net_info['color'] if style == 'colored' else mono_color
            letter = network_letters.get(net_key, net_key[0].upper())
            
            if style == 'colored':
                bg = color
                text_color = "#ffffff"
                border = "none"
            elif style == 'outline':
                bg = "transparent"
                text_color = color
                border = f"2px solid {color}"
            else:  # mono
                bg = mono_color
                text_color = "#ffffff"
                border = "none"
            
            # Utiliser table pour meilleure compatibilité email
            icons_html += f'''<a href="{url}" target="_blank" title="{net_info['name']}" style="display:inline-block;width:{size}px;height:{size}px;background:{bg};border-radius:{border_radius}%;text-align:center;line-height:{size}px;text-decoration:none;font-size:{size//3}px;font-weight:bold;color:{text_color};margin:0 {gap//2}px;border:{border};font-family:Arial,sans-serif;vertical-align:middle;">{letter}</a>'''
        
        return f'<div style="text-align:{align};padding:15px 0;">{icons_html}</div>'
    
    def get_preview_text(self):
        networks = self.content.get('networks', {})
        active = [k for k, v in networks.items() if v]
        return f"🔗 {len(active)} réseau(x): {', '.join(active[:3])}{'...' if len(active) > 3 else ''}"


class HtmlBlock(EmailBlock):
    BLOCK_TYPE = "html"
    BLOCK_ICON = "🔧"
    BLOCK_NAME = "HTML"
    
    @classmethod
    def get_default_content(cls): return {"html": ""}
    def to_html(self, context=None): return self.content['html']
    def get_preview_text(self): return "🔧 HTML personnalisé"


class ImageGridBlock(EmailBlock):
    """Grille d'images flexible (2, 3 ou 4 colonnes)"""
    BLOCK_TYPE = "image_grid"
    BLOCK_ICON = "🖼️"
    BLOCK_NAME = "Grille Images"
    
    @classmethod
    def get_default_content(cls):
        return {"images": [], "columns": 2, "gap": 15, "border_radius": 12,
                "aspect_ratio": "auto", "shadow": True, "padding": 10,
                "captions": True, "caption_style": "overlay", "hover_effect": "zoom"}
    
    def to_html(self, context=None):
        c = self.content
        images = c.get('images', [])
        if not images: return ""
        
        columns = c.get('columns', 2)
        gap = c.get('gap', 15)
        border_radius = c.get('border_radius', 12)
        shadow_enabled = c.get('shadow', True)
        padding = c.get('padding', 10)
        captions_enabled = c.get('captions', True)
        caption_style = c.get('caption_style', 'overlay')
        aspect_ratio = c.get('aspect_ratio', 'auto')
        
        col_width = f"{100 // columns - 2}%"
        shadow = "box-shadow:0 4px 15px rgba(0,0,0,0.1);" if shadow_enabled else ""
        
        images_html = ""
        for img in images:
            url = img.get('url', '')
            caption = img.get('caption', '')
            link = img.get('link', '')
            
            if not url: continue
            
            img_style = f"width:100%;border-radius:{border_radius}px;{shadow}"
            if aspect_ratio != "auto":
                img_style += f"aspect-ratio:{aspect_ratio};object-fit:cover;"
            
            img_html = f'<img src="{url}" alt="{caption}" style="{img_style}">'
            
            if link:
                img_html = f'<a href="{link}" target="_blank" style="text-decoration:none;">{img_html}</a>'
            
            caption_html = ""
            if caption and captions_enabled:
                if caption_style == "overlay":
                    caption_html = f'<div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,0.7));padding:15px;border-radius:0 0 {border_radius}px {border_radius}px;"><p style="margin:0;color:white;font-size:13px;">{caption}</p></div>'
                else:
                    caption_html = f'<p style="margin:8px 0 0 0;color:#666;font-size:12px;text-align:center;">{caption}</p>'
            
            cell_style = f"width:{col_width};display:inline-block;vertical-align:top;padding:{gap//2}px;position:relative;"
            images_html += f'<div style="{cell_style}">{img_html}{caption_html}</div>'
        
        return f'<div style="padding:{padding}px;text-align:center;font-size:0;">{images_html}</div>'
    
    def get_preview_text(self):
        return f"🖼️ Grille: {len(self.content.get('images', []))} images ({self.content.get('columns', 2)} col.)"


class ColumnsBlock(EmailBlock):
    """Bloc multi-colonnes flexible"""
    BLOCK_TYPE = "columns"
    BLOCK_ICON = "📊"
    BLOCK_NAME = "Colonnes"
    
    @classmethod
    def get_default_content(cls):
        return {"columns": [
            {"width": "50%", "content": "", "align": "left", "valign": "top", "padding": 15, "bg_color": "transparent"},
            {"width": "50%", "content": "", "align": "left", "valign": "top", "padding": 15, "bg_color": "transparent"}
        ], "gap": 20, "mobile_stack": True, "border_between": False, "border_color": "#e0e0e0"}
    
    def to_html(self, context=None):
        c = self.content
        cols_html = ""
        columns = c.get('columns', [])
        border_between = c.get('border_between', False)
        border_color = c.get('border_color', '#e0e0e0')
        
        for i, col in enumerate(columns):
            border = ""
            if border_between and i > 0:
                border = f"border-left:1px solid {border_color};"
            
            width = col.get('width', '50%')
            valign = col.get('valign', 'top')
            padding = col.get('padding', 15)
            align = col.get('align', 'left')
            bg_color = col.get('bg_color', 'transparent')
            content = col.get('content', '')
            
            style = f"width:{width};display:inline-block;vertical-align:{valign};padding:{padding}px;text-align:{align};background-color:{bg_color};{border}"
            cols_html += f'<div style="{style}">{content}</div>'
        
        return f'<div style="font-size:0;text-align:center;">{cols_html}</div>'
    
    def get_preview_text(self):
        return f"📊 {len(self.content.get('columns', []))} colonnes"


class HeroBlock(EmailBlock):
    """Image héro avec texte superposé"""
    BLOCK_TYPE = "hero"
    BLOCK_ICON = "🎯"
    BLOCK_NAME = "Héro"
    
    @classmethod
    def get_default_content(cls):
        return {"image_url": "", "height": 400, "overlay": True, "overlay_color": "rgba(0,0,0,0.4)",
                "title": "", "title_size": 36, "title_color": "#ffffff",
                "subtitle": "", "subtitle_size": 18, "subtitle_color": "rgba(255,255,255,0.9)",
                "text_align": "center", "text_valign": "center", "button_text": "",
                "button_url": "", "button_style": "gradient", "padding": 40}
    
    def to_html(self, context=None):
        c = self.content
        image_url = c.get('image_url', '')
        height = c.get('height', 400)
        overlay_enabled = c.get('overlay', True)
        overlay_color = c.get('overlay_color', 'rgba(0,0,0,0.4)')
        title = c.get('title', '')
        title_size = c.get('title_size', 36)
        title_color = c.get('title_color', '#ffffff')
        subtitle = c.get('subtitle', '')
        subtitle_size = c.get('subtitle_size', 18)
        subtitle_color = c.get('subtitle_color', 'rgba(255,255,255,0.9)')
        text_align = c.get('text_align', 'center')
        text_valign = c.get('text_valign', 'center')
        button_text = c.get('button_text', '')
        button_url = c.get('button_url', '')
        button_style = c.get('button_style', 'gradient')
        padding = c.get('padding', 40)
        
        bg_style = f"background-image:url('{image_url}');background-size:cover;background-position:center;" if image_url else f"background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});"
        overlay = f'<div style="position:absolute;top:0;left:0;right:0;bottom:0;background:{overlay_color};"></div>' if overlay_enabled and image_url else ""
        
        # Alignement vertical
        justify = "center"
        if text_valign == "top": justify = "flex-start"
        elif text_valign == "bottom": justify = "flex-end"
        
        title_html = f'<h1 style="margin:0 0 15px 0;color:{title_color};font-size:{title_size}px;font-weight:bold;">{title}</h1>' if title else ""
        subtitle_html = f'<p style="margin:0 0 25px 0;color:{subtitle_color};font-size:{subtitle_size}px;line-height:1.6;">{subtitle}</p>' if subtitle else ""
        
        button = ""
        if button_text and button_url:
            if button_style == "gradient":
                btn_style = f"background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});color:white;"
            elif button_style == "outline":
                btn_style = "background:transparent;border:2px solid white;color:white;"
            else:
                btn_style = f"background:{KRYSTO_PRIMARY};color:white;"
            button = f'<a href="{button_url}" style="display:inline-block;padding:14px 35px;{btn_style}text-decoration:none;border-radius:25px;font-weight:bold;font-size:15px;">{button_text}</a>'
        
        content = f'<div style="position:relative;z-index:1;display:flex;flex-direction:column;justify-content:{justify};align-items:{text_align};height:100%;padding:{padding}px;text-align:{text_align};">{title_html}{subtitle_html}{button}</div>'
        
        return f'<div style="position:relative;height:{height}px;{bg_style}overflow:hidden;">{overlay}{content}</div>'
    
    def get_preview_text(self):
        return f"🎯 Héro: {self.content.get('title', '') or 'Sans titre'}"


class CardBlock(EmailBlock):
    """Carte avec image et contenu"""
    BLOCK_TYPE = "card"
    BLOCK_ICON = "🃏"
    BLOCK_NAME = "Carte"
    
    @classmethod
    def get_default_content(cls):
        return {"image_url": "", "image_position": "top", "image_height": 200,
                "title": "", "title_size": 20, "title_color": KRYSTO_DARK,
                "description": "", "description_size": 14, "description_color": "#666666",
                "button_text": "", "button_url": "", "button_style": "gradient",
                "bg_color": "#ffffff", "border_radius": 15, "shadow": True,
                "padding": 25, "border": False, "border_color": "#e0e0e0"}
    
    def to_html(self, context=None):
        c = self.content
        shadow_enabled = c.get('shadow', True)
        border_enabled = c.get('border', False)
        border_color = c.get('border_color', '#e0e0e0')
        border_radius = c.get('border_radius', 15)
        bg_color = c.get('bg_color', '#ffffff')
        padding = c.get('padding', 25)
        image_url = c.get('image_url', '')
        image_position = c.get('image_position', 'top')
        image_height = c.get('image_height', 200)
        title = c.get('title', '')
        title_size = c.get('title_size', 20)
        title_color = c.get('title_color', KRYSTO_DARK)
        description = c.get('description', '')
        description_size = c.get('description_size', 14)
        description_color = c.get('description_color', '#666666')
        button_text = c.get('button_text', '')
        button_url = c.get('button_url', '')
        button_style = c.get('button_style', 'gradient')
        
        shadow = "box-shadow:0 8px 30px rgba(0,0,0,0.12);" if shadow_enabled else ""
        border = f"border:1px solid {border_color};" if border_enabled else ""
        
        image = ""
        if image_url:
            img_radius = f"{border_radius}px {border_radius}px 0 0" if image_position == "top" else f"0 0 {border_radius}px {border_radius}px"
            image = f'<img src="{image_url}" style="width:100%;height:{image_height}px;object-fit:cover;border-radius:{img_radius};display:block;">'
        
        title_html = f'<h3 style="margin:0 0 12px 0;color:{title_color};font-size:{title_size}px;font-weight:bold;">{title}</h3>' if title else ""
        desc = f'<p style="margin:0 0 20px 0;color:{description_color};font-size:{description_size}px;line-height:1.6;">{description}</p>' if description else ""
        
        button = ""
        if button_text and button_url:
            if button_style == "gradient":
                btn_style = f"background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});color:white;border:none;"
            elif button_style == "outline":
                btn_style = f"background:transparent;border:2px solid {KRYSTO_PRIMARY};color:{KRYSTO_PRIMARY};"
            else:
                btn_style = f"background:{KRYSTO_PRIMARY};color:white;border:none;"
            button = f'<a href="{button_url}" style="display:inline-block;padding:12px 28px;{btn_style}text-decoration:none;border-radius:20px;font-weight:bold;font-size:14px;">{button_text}</a>'
        
        content = f'<div style="padding:{padding}px;">{title_html}{desc}{button}</div>'
        
        if image_position == "top":
            inner = f'{image}{content}'
        else:
            inner = f'{content}{image}'
        
        return f'<div style="background-color:{bg_color};border-radius:{border_radius}px;{shadow}{border}overflow:hidden;">{inner}</div>'
    
    def get_preview_text(self):
        return f"🃏 Carte: {self.content.get('title', '') or 'Sans titre'}"


class ProductBlock(EmailBlock):
    """Mise en avant d'un produit"""
    BLOCK_TYPE = "product"
    BLOCK_ICON = "🛍️"
    BLOCK_NAME = "Produit"
    
    @classmethod
    def get_default_content(cls):
        return {"image_url": "", "name": "", "description": "", "price": "",
                "old_price": "", "badge": "", "badge_color": "#ff6b6b",
                "cta_text": "Commander", "cta_url": "", "layout": "horizontal",
                "image_width": "40%", "border_radius": 12, "shadow": True}
    
    def to_html(self, context=None):
        c = self.content
        shadow_enabled = c.get('shadow', True)
        border_radius = c.get('border_radius', 12)
        layout = c.get('layout', 'horizontal')
        image_url = c.get('image_url', '')
        image_width = c.get('image_width', '40%')
        name = c.get('name', '')
        description = c.get('description', '')
        price = c.get('price', '')
        old_price = c.get('old_price', '')
        badge_text = c.get('badge', '')
        badge_color = c.get('badge_color', '#ff6b6b')
        cta_text = c.get('cta_text', 'Commander')
        cta_url = c.get('cta_url', '')
        
        shadow = "box-shadow:0 8px 30px rgba(0,0,0,0.1);" if shadow_enabled else ""
        
        badge = ""
        if badge_text:
            badge = f'<span style="position:absolute;top:15px;left:15px;background:{badge_color};color:white;padding:5px 12px;border-radius:15px;font-size:12px;font-weight:bold;">{badge_text}</span>'
        
        image = ""
        if image_url:
            image = f'<div style="position:relative;{"width:" + image_width + ";" if layout == "horizontal" else ""}"><img src="{image_url}" style="width:100%;border-radius:{border_radius}px;display:block;">{badge}</div>'
        
        old_price_html = f'<span style="text-decoration:line-through;color:#999;font-size:14px;margin-right:10px;">{old_price}</span>' if old_price else ""
        price_html = f'<div style="margin:15px 0;">{old_price_html}<span style="color:{KRYSTO_PRIMARY};font-size:24px;font-weight:bold;">{price}</span></div>' if price else ""
        
        cta = ""
        if cta_text and cta_url:
            cta = f'<a href="{cta_url}" style="display:inline-block;padding:12px 30px;background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});color:white;text-decoration:none;border-radius:25px;font-weight:bold;font-size:14px;">{cta_text}</a>'
        
        info = f'''<div style="{"flex:1;padding-left:25px;" if layout == "horizontal" else "padding:20px 0;"}">
            <h3 style="margin:0 0 10px 0;color:{KRYSTO_DARK};font-size:22px;font-weight:bold;">{name}</h3>
            <p style="margin:0;color:#666;font-size:14px;line-height:1.6;">{description}</p>
            {price_html}{cta}
        </div>'''
        
        if layout == "horizontal":
            return f'<div style="display:flex;align-items:center;background:white;padding:20px;border-radius:{border_radius}px;{shadow}">{image}{info}</div>'
        else:
            return f'<div style="background:white;padding:20px;border-radius:{border_radius}px;{shadow}text-align:center;">{image}{info}</div>'
    
    def get_preview_text(self):
        return f"🛍️ Produit: {self.content.get('name', '') or 'Sans nom'}"


class TestimonialBlock(EmailBlock):
    """Témoignage client"""
    BLOCK_TYPE = "testimonial"
    BLOCK_ICON = "💬"
    BLOCK_NAME = "Témoignage"
    
    @classmethod
    def get_default_content(cls):
        return {"quote": "", "author_name": "", "author_title": "", "author_image": "",
                "rating": 5, "show_stars": True, "style": "card", "bg_color": "#f8f9fa",
                "accent_color": KRYSTO_PRIMARY, "border_radius": 15}
    
    def to_html(self, context=None):
        c = self.content
        quote = c.get('quote', '')
        author_name = c.get('author_name', '')
        author_title_text = c.get('author_title', '')
        author_image = c.get('author_image', '')
        rating = c.get('rating', 5)
        show_stars = c.get('show_stars', True)
        style = c.get('style', 'card')
        bg_color = c.get('bg_color', '#f8f9fa')
        accent_color = c.get('accent_color', KRYSTO_PRIMARY)
        border_radius = c.get('border_radius', 15)
        
        stars = ""
        if show_stars and rating > 0:
            stars = f'<div style="margin-bottom:15px;">{"⭐" * rating}</div>'
        
        avatar = ""
        if author_image:
            avatar = f'<img src="{author_image}" style="width:50px;height:50px;border-radius:50%;object-fit:cover;margin-right:15px;">'
        
        author_title_html = f'<span style="color:#888;font-size:13px;">{author_title_text}</span>' if author_title_text else ""
        
        author = f'''<div style="display:flex;align-items:center;margin-top:20px;">
            {avatar}
            <div>
                <strong style="color:{KRYSTO_DARK};font-size:15px;">{author_name}</strong><br>
                {author_title_html}
            </div>
        </div>'''
        
        if style == "card":
            return f'''<div style="background:{bg_color};padding:30px;border-radius:{border_radius}px;border-left:4px solid {accent_color};">
                {stars}
                <p style="margin:0;color:{KRYSTO_DARK};font-size:16px;line-height:1.7;font-style:italic;">"{quote}"</p>
                {author}
            </div>'''
        else:
            return f'''<div style="text-align:center;padding:30px;">
                {stars}
                <p style="margin:0 0 20px 0;color:{KRYSTO_DARK};font-size:18px;line-height:1.7;font-style:italic;">"{quote}"</p>
                <div style="display:inline-flex;align-items:center;">{avatar}<div style="text-align:left;"><strong>{author_name}</strong><br><span style="color:#888;font-size:13px;">{author_title_text}</span></div></div>
            </div>'''
    
    def get_preview_text(self):
        return f"💬 {self.content.get('author_name', '') or 'Témoignage'}"


class VideoBlock(EmailBlock):
    """Aperçu vidéo avec lien"""
    BLOCK_TYPE = "video"
    BLOCK_ICON = "🎬"
    BLOCK_NAME = "Vidéo"
    
    @classmethod
    def get_default_content(cls):
        return {"thumbnail_url": "", "video_url": "", "title": "", "duration": "",
                "play_button_color": KRYSTO_PRIMARY, "border_radius": 12, "shadow": True}
    
    def to_html(self, context=None):
        c = self.content
        shadow = "box-shadow:0 8px 30px rgba(0,0,0,0.15);" if c.get('shadow', True) else ""
        play_color = c.get('play_button_color', KRYSTO_PRIMARY)
        border_radius = c.get('border_radius', 12)
        thumbnail = c.get('thumbnail_url', '')
        video_url = c.get('video_url', '')
        title = c.get('title', '')
        duration = c.get('duration', '')
        
        if not thumbnail:
            return ""
        
        play_btn = f'''<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:70px;height:70px;background:{play_color};border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 20px rgba(0,0,0,0.3);">
            <span style="color:white;font-size:30px;margin-left:5px;">▶</span>
        </div>'''
        
        duration_html = f'<span style="position:absolute;bottom:15px;right:15px;background:rgba(0,0,0,0.7);color:white;padding:4px 10px;border-radius:4px;font-size:12px;">{duration}</span>' if duration else ""
        
        title_html = f'<p style="margin:15px 0 0 0;color:{KRYSTO_DARK};font-size:16px;font-weight:bold;text-align:center;">{title}</p>' if title else ""
        
        return f'''<div style="padding:10px;">
            <a href="{video_url}" target="_blank" style="display:block;position:relative;border-radius:{border_radius}px;overflow:hidden;{shadow}">
                <img src="{thumbnail}" style="width:100%;display:block;">
                {play_btn}{duration_html}
            </a>
            {title_html}
        </div>'''
    
    def get_preview_text(self):
        return f"🎬 Vidéo: {self.content.get('title', '') or 'Sans titre'}"


class CountdownBlock(EmailBlock):
    """Compte à rebours (affichage statique)"""
    BLOCK_TYPE = "countdown"
    BLOCK_ICON = "⏱️"
    BLOCK_NAME = "Compte à rebours"
    
    @classmethod
    def get_default_content(cls):
        return {"title": "Offre expire dans:", "days": "03", "hours": "12", "minutes": "45",
                "style": "boxes", "bg_color": KRYSTO_DARK, "text_color": "#ffffff",
                "accent_color": KRYSTO_SECONDARY, "border_radius": 10}
    
    def to_html(self, context=None):
        c = self.content
        bg_color = c.get('bg_color', KRYSTO_DARK)
        text_color = c.get('text_color', '#ffffff')
        accent_color = c.get('accent_color', KRYSTO_SECONDARY)
        border_radius = c.get('border_radius', 10)
        title = c.get('title', '')
        days = c.get('days', '03')
        hours = c.get('hours', '12')
        minutes = c.get('minutes', '45')
        
        box_style = f"display:inline-block;background:{bg_color};color:{text_color};padding:15px 20px;margin:5px;border-radius:{border_radius}px;text-align:center;min-width:60px;"
        
        units = [(days, "JOURS"), (hours, "HEURES"), (minutes, "MIN")]
        boxes = ""
        for val, label in units:
            boxes += f'''<div style="{box_style}">
                <div style="font-size:28px;font-weight:bold;">{val}</div>
                <div style="font-size:10px;color:{accent_color};margin-top:5px;">{label}</div>
            </div>'''
        
        title_html = f'<p style="margin:0 0 20px 0;color:{KRYSTO_DARK};font-size:16px;font-weight:bold;">{title}</p>' if title else ""
        
        return f'<div style="text-align:center;padding:20px;">{title_html}{boxes}</div>'
    
    def get_preview_text(self):
        return f"⏱️ {self.content.get('days', '03')}j {self.content.get('hours', '12')}h {self.content.get('minutes', '45')}m"


class GalleryBlock(EmailBlock):
    """Galerie avec image principale + miniatures"""
    BLOCK_TYPE = "gallery"
    BLOCK_ICON = "🎨"
    BLOCK_NAME = "Galerie"
    
    @classmethod
    def get_default_content(cls):
        return {"images": [], "main_height": 350, "thumb_size": 80, "gap": 10,
                "border_radius": 12, "shadow": True, "caption": ""}
    
    def to_html(self, context=None):
        c = self.content
        images = c.get('images', [])
        if not images: return ""
        
        main_height = c.get('main_height', 350)
        thumb_size = c.get('thumb_size', 80)
        gap = c.get('gap', 10)
        border_radius = c.get('border_radius', 12)
        shadow_enabled = c.get('shadow', True)
        caption = c.get('caption', '')
        
        shadow = "box-shadow:0 4px 15px rgba(0,0,0,0.1);" if shadow_enabled else ""
        
        main_img = images[0] if images else {}
        main_html = f'<img src="{main_img.get("url", "")}" style="width:100%;height:{main_height}px;object-fit:cover;border-radius:{border_radius}px;{shadow}">' if main_img.get('url') else ""
        
        thumbs = ""
        if len(images) > 1:
            for img in images[1:]:
                url = img.get('url', '')
                if url:
                    link = img.get('link', url)
                    thumbs += f'<a href="{link}" target="_blank"><img src="{url}" style="width:{thumb_size}px;height:{thumb_size}px;object-fit:cover;border-radius:8px;margin:{gap//2}px;"></a>'
            thumbs = f'<div style="margin-top:{gap}px;text-align:center;">{thumbs}</div>'
        
        caption_html = f'<p style="margin:15px 0 0 0;color:#666;font-size:14px;text-align:center;line-height:1.6;">{caption}</p>' if caption else ""
        
        return f'<div style="padding:10px;">{main_html}{thumbs}{caption_html}</div>'
    
    def get_preview_text(self):
        return f"🎨 Galerie: {len(self.content.get('images', []))} images"


class AccordionBlock(EmailBlock):
    """FAQ / Accordéon (déplié en email)"""
    BLOCK_TYPE = "accordion"
    BLOCK_ICON = "📚"
    BLOCK_NAME = "FAQ"
    
    @classmethod
    def get_default_content(cls):
        return {"items": [{"question": "", "answer": ""}], "style": "bordered",
                "accent_color": KRYSTO_PRIMARY, "bg_color": "#f8f9fa", "border_radius": 10}
    
    def to_html(self, context=None):
        c = self.content
        items_html = ""
        border_radius = c.get('border_radius', 10)
        bg_color = c.get('bg_color', '#f8f9fa')
        accent_color = c.get('accent_color', KRYSTO_PRIMARY)
        style = c.get('style', 'bordered')
        
        for item in c.get('items', []):
            q = item.get('question', '')
            a = item.get('answer', '')
            if not q: continue
            
            if style == "bordered":
                items_html += f'''<div style="border:1px solid #e0e0e0;border-radius:{border_radius}px;margin-bottom:10px;overflow:hidden;">
                    <div style="background:{bg_color};padding:15px 20px;font-weight:bold;color:{KRYSTO_DARK};border-left:4px solid {accent_color};">{q}</div>
                    <div style="padding:15px 20px;color:#666;line-height:1.6;">{a}</div>
                </div>'''
            else:
                items_html += f'''<div style="margin-bottom:15px;">
                    <p style="margin:0 0 8px 0;font-weight:bold;color:{accent_color};">❓ {q}</p>
                    <p style="margin:0;color:#666;line-height:1.6;padding-left:20px;">{a}</p>
                </div>'''
        
        return f'<div style="padding:10px;">{items_html}</div>'
    
    def get_preview_text(self):
        return f"📚 FAQ: {len(self.content.get('items', []))} questions"


class StatsBlock(EmailBlock):
    """Statistiques / Chiffres clés"""
    BLOCK_TYPE = "stats"
    BLOCK_ICON = "📈"
    BLOCK_NAME = "Statistiques"
    
    @classmethod
    def get_default_content(cls):
        return {"stats": [{"value": "100+", "label": "Clients"}, {"value": "500", "label": "Projets"}],
                "columns": 3, "style": "cards", "bg_color": KRYSTO_DARK, "value_color": KRYSTO_SECONDARY,
                "label_color": "#ffffff", "value_size": 36, "border_radius": 10}
    
    def to_html(self, context=None):
        c = self.content
        stats = c.get('stats', [])
        columns = c.get('columns', 3)
        style = c.get('style', 'cards')
        bg_color = c.get('bg_color', KRYSTO_DARK)
        value_color = c.get('value_color', KRYSTO_SECONDARY)
        label_color = c.get('label_color', '#ffffff')
        value_size = c.get('value_size', 36)
        border_radius = c.get('border_radius', 10)
        
        if not stats: return ""
        
        col_width = f"{100 // min(len(stats), columns)}%"
        
        stats_html = ""
        for stat in stats:
            value = stat.get('value', '')
            label = stat.get('label', '')
            
            if style == "cards":
                stats_html += f'''<div style="display:inline-block;width:{col_width};padding:10px;vertical-align:top;text-align:center;">
                    <div style="background:{bg_color};padding:25px;border-radius:{border_radius}px;">
                        <div style="color:{value_color};font-size:{value_size}px;font-weight:bold;">{value}</div>
                        <div style="color:{label_color};font-size:14px;margin-top:8px;">{label}</div>
                    </div>
                </div>'''
            else:
                stats_html += f'''<div style="display:inline-block;width:{col_width};padding:20px;vertical-align:top;text-align:center;">
                    <div style="color:{value_color};font-size:{value_size}px;font-weight:bold;">{value}</div>
                    <div style="color:{KRYSTO_DARK};font-size:14px;margin-top:5px;">{label}</div>
                </div>'''
        
        return f'<div style="text-align:center;font-size:0;">{stats_html}</div>'
    
    def get_preview_text(self):
        return f"📈 {len(self.content.get('stats', []))} stats"


class MapBlock(EmailBlock):
    """Image de carte statique avec lien Google Maps"""
    BLOCK_TYPE = "map"
    BLOCK_ICON = "📍"
    BLOCK_NAME = "Carte"
    
    @classmethod
    def get_default_content(cls):
        return {
            "address": COMPANY_ADDRESS,
            "maps_url": "",  # Lien cliquable vers Google Maps
            "image_url": "",  # URL image statique (screenshot ou API)
            "api_key": "",  # Clé API Google Maps (optionnel)
            "zoom": 15,
            "height": 250,
            "border_radius": 12,
            "show_address": True,
            "map_type": "roadmap",  # roadmap, satellite, terrain, hybrid
            "marker_color": "red"
        }
    
    def get_static_map_url(self):
        """Génère l'URL Google Maps Static API si clé disponible."""
        c = self.content
        api_key = c.get('api_key', '')
        address = c.get('address', '')
        zoom = c.get('zoom', 15)
        map_type = c.get('map_type', 'roadmap')
        marker_color = c.get('marker_color', 'red')
        
        if not api_key or not address:
            return None
        
        # Encoder l'adresse pour l'URL
        import urllib.parse
        encoded_address = urllib.parse.quote(address)
        
        return f"https://maps.googleapis.com/maps/api/staticmap?center={encoded_address}&zoom={zoom}&size=600x300&maptype={map_type}&markers=color:{marker_color}%7C{encoded_address}&key={api_key}"
    
    def get_maps_link(self):
        """Génère le lien Google Maps pour l'adresse."""
        c = self.content
        address = c.get('address', '')
        if c.get('maps_url'):
            return c.get('maps_url')
        if address:
            import urllib.parse
            return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"
        return ""
    
    def to_html(self, context=None):
        c = self.content
        address = c.get('address', COMPANY_ADDRESS)
        height = c.get('height', 250)
        border_radius = c.get('border_radius', 12)
        show_address = c.get('show_address', True)
        
        # Utiliser l'URL fournie ou générer via API
        image_url = c.get('image_url', '')
        if not image_url:
            image_url = self.get_static_map_url()
        
        if not image_url:
            # Afficher un placeholder si pas d'image
            return f'''<div style="padding:10px;">
                <div style="height:{height}px;border-radius:{border_radius}px;background:linear-gradient(135deg,#e8e8e8,#f5f5f5);display:flex;align-items:center;justify-content:center;">
                    <div style="text-align:center;color:#888;">
                        <div style="font-size:40px;">📍</div>
                        <p style="margin:10px 0 0 0;font-size:14px;">{address}</p>
                    </div>
                </div>
            </div>'''
        
        maps_link = self.get_maps_link()
        
        address_overlay = ""
        if show_address and address:
            address_overlay = f'''<div style="background:rgba(255,255,255,0.95);padding:12px 20px;border-radius:8px;position:absolute;bottom:15px;left:15px;right:15px;box-shadow:0 2px 10px rgba(0,0,0,0.1);">
                <p style="margin:0;color:{KRYSTO_DARK};font-size:14px;">📍 {address}</p>
            </div>'''
        
        map_content = f'''<div style="position:relative;height:{height}px;border-radius:{border_radius}px;overflow:hidden;">
            <img src="{image_url}" style="width:100%;height:100%;object-fit:cover;">
            {address_overlay}
        </div>'''
        
        if maps_link:
            map_content = f'<a href="{maps_link}" target="_blank" style="display:block;text-decoration:none;">{map_content}</a>'
        
        return f'<div style="padding:10px;">{map_content}</div>'
    
    def get_preview_text(self):
        addr = self.content.get('address', '')
        has_image = bool(self.content.get('image_url') or self.content.get('api_key'))
        status = "✓" if has_image else "⚠️"
        return f"📍 {status} {addr[:25]}..." if len(addr) > 25 else f"📍 {status} {addr}"


class FooterLinksBlock(EmailBlock):
    """Liens de pied de page"""
    BLOCK_TYPE = "footer_links"
    BLOCK_ICON = "🔗"
    BLOCK_NAME = "Liens footer"
    
    @classmethod
    def get_default_content(cls):
        return {"links": [{"text": "Site web", "url": f"https://{COMPANY_WEBSITE}"},
                          {"text": "Contact", "url": f"mailto:{COMPANY_EMAIL}"}],
                "separator": " | ", "align": "center", "color": "#888888", "font_size": 13}
    
    def to_html(self, context=None):
        c = self.content
        links_list = c.get('links', [])
        separator = c.get('separator', ' | ')
        align = c.get('align', 'center')
        color = c.get('color', '#888888')
        font_size = c.get('font_size', 13)
        
        links = [f'<a href="{l.get("url", "")}" style="color:{color};text-decoration:underline;">{l.get("text", "")}</a>' for l in links_list if l.get('url')]
        return f'<div style="text-align:{align};padding:15px;font-size:{font_size}px;">{separator.join(links)}</div>'
    
    def get_preview_text(self):
        return f"🔗 {len(self.content.get('links', []))} liens"


class UnsubscribeBlock(EmailBlock):
    """Bouton de désinscription avec notification email à l'admin"""
    BLOCK_TYPE = "unsubscribe"
    BLOCK_ICON = "🚫"
    BLOCK_NAME = "Désinscription"
    
    @classmethod
    def get_default_content(cls):
        return {
            "text": "Se désinscrire",
            "admin_email": "contact@krysto.nc",
            "style": "link",  # link, button, discrete
            "color": "#888888",
            "font_size": 12,
            "show_info": True,  # Afficher texte explicatif
            "info_text": "Vous ne souhaitez plus recevoir nos emails ?"
        }
    
    def to_html(self, context=None):
        c = self.content
        text = c.get('text', 'Se désinscrire')
        admin_email = c.get('admin_email', 'contact@krysto.nc')
        color = c.get('color', '#888888')
        font_size = c.get('font_size', 12)
        style = c.get('style', 'link')
        show_info = c.get('show_info', True)
        info_text = c.get('info_text', '')
        
        # Utiliser les variables du contexte si disponibles
        client_email = context.get('email', '') if context else '{{email}}'
        client_name = context.get('name', '') if context else '{{name}}'
        
        # Créer le mailto vers l'admin avec les infos du client
        import urllib.parse
        
        subject = f"🚫 Demande de désinscription newsletter"
        body = f"""⚠️ DEMANDE DE DÉSINSCRIPTION

Un client souhaite se désinscrire de la newsletter KRYSTO.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email: {client_email}
👤 Nom: {client_name}
📅 Date: {{{{date}}}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Action requise:
1. Ouvrir KRYSTO Manager
2. Aller dans Clients
3. Rechercher ce client
4. Décocher "Newsletter"

Ce message a été généré automatiquement suite à une demande de désinscription.
"""
        
        encoded_subject = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(body)
        mailto_link = f"mailto:{admin_email}?subject={encoded_subject}&body={encoded_body}"
        
        # Lien de confirmation (page data: qui affiche un message)
        confirm_html = urllib.parse.quote(f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Désinscription</title>
<style>body{{font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY})}}
.box{{background:white;padding:50px;border-radius:20px;text-align:center;max-width:400px;box-shadow:0 20px 60px rgba(0,0,0,0.3)}}
h1{{color:{KRYSTO_DARK};margin:0 0 20px}}p{{color:#666;line-height:1.6}}.icon{{font-size:60px;margin-bottom:20px}}</style></head>
<body><div class="box"><div class="icon">✅</div><h1>Demande envoyée</h1><p>Votre demande de désinscription a été transmise à notre équipe.</p><p>Vous serez retiré de notre liste sous 48h.</p><p style="margin-top:30px;font-size:12px;color:#888;">Vous pouvez fermer cette page.</p></div></body></html>''')
        
        info_html = f'<p style="margin:0 0 8px 0;color:#aaa;font-size:{font_size}px;">{info_text}</p>' if show_info and info_text else ""
        
        # JavaScript pour ouvrir mailto ET afficher confirmation
        onclick = f"window.open('{mailto_link}');window.location='data:text/html;charset=utf-8,{confirm_html}';return false;"
        
        if style == "button":
            return f'''<div style="text-align:center;padding:20px;background:#f8f8f8;border-radius:8px;margin-top:20px;">
                {info_html}
                <a href="{mailto_link}" onclick="{onclick}" style="display:inline-block;padding:10px 25px;background:{color};color:white;text-decoration:none;border-radius:20px;font-size:{font_size}px;">{text}</a>
            </div>'''
        elif style == "discrete":
            return f'''<div style="text-align:center;padding:10px;border-top:1px solid #eee;margin-top:20px;">
                <a href="{mailto_link}" onclick="{onclick}" style="color:{color};font-size:{font_size - 1}px;text-decoration:none;">{text}</a>
            </div>'''
        else:  # link
            return f'''<div style="text-align:center;padding:15px;">
                {info_html}
                <a href="{mailto_link}" onclick="{onclick}" style="color:{color};font-size:{font_size}px;text-decoration:underline;">{text}</a>
            </div>'''
    
    def get_preview_text(self):
        return f"🚫 Désinscription → {self.content.get('admin_email', 'contact@krysto.nc')}"


class SignatureBlock(EmailBlock):
    """Signature email professionnelle"""
    BLOCK_TYPE = "signature"
    BLOCK_ICON = "✍️"
    BLOCK_NAME = "Signature"
    
    @classmethod
    def get_default_content(cls):
        return {
            "name": "L'équipe KRYSTO",
            "title": "",
            "company": COMPANY_NAME,
            "phone": COMPANY_PHONE,
            "email": COMPANY_EMAIL,
            "website": COMPANY_WEBSITE,
            "logo_url": "",
            "photo_url": "",
            "style": "modern",  # modern, classic, minimal
            "accent_color": KRYSTO_PRIMARY
        }
    
    def to_html(self, context=None):
        c = self.content
        name = c.get('name', '')
        title = c.get('title', '')
        company = c.get('company', COMPANY_NAME)
        phone = c.get('phone', '')
        email = c.get('email', '')
        website = c.get('website', '')
        logo_url = c.get('logo_url', '')
        photo_url = c.get('photo_url', '')
        style = c.get('style', 'modern')
        accent = c.get('accent_color', KRYSTO_PRIMARY)
        
        photo_html = f'<img src="{photo_url}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;margin-right:15px;">' if photo_url else ""
        logo_html = f'<img src="{logo_url}" style="height:40px;margin-top:10px;">' if logo_url else ""
        title_html = f'<span style="color:#888;font-size:13px;">{title}</span><br>' if title else ""
        
        contact_lines = []
        if phone: contact_lines.append(f'📞 {phone}')
        if email: contact_lines.append(f'✉️ <a href="mailto:{email}" style="color:{accent};text-decoration:none;">{email}</a>')
        if website: contact_lines.append(f'🌐 <a href="https://{website}" style="color:{accent};text-decoration:none;">{website}</a>')
        contact_html = '<br>'.join(contact_lines)
        
        if style == "modern":
            return f'''<div style="padding:20px 0;border-top:3px solid {accent};">
                <table cellpadding="0" cellspacing="0" border="0"><tr>
                    <td style="vertical-align:top;">{photo_html}</td>
                    <td style="vertical-align:top;">
                        <strong style="color:{KRYSTO_DARK};font-size:16px;">{name}</strong><br>
                        {title_html}
                        <span style="color:{accent};font-weight:bold;">{company}</span>
                        <div style="margin-top:10px;font-size:13px;color:#666;line-height:1.8;">{contact_html}</div>
                        {logo_html}
                    </td>
                </tr></table>
            </div>'''
        elif style == "classic":
            return f'''<div style="padding:20px;border:1px solid #e0e0e0;border-radius:8px;background:#fafafa;">
                <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
                    <td>{photo_html}<strong style="font-size:15px;">{name}</strong>{" - " + title if title else ""}<br>
                    <span style="color:{accent};">{company}</span></td>
                    <td style="text-align:right;font-size:12px;color:#666;">{contact_html}</td>
                </tr></table>
            </div>'''
        else:  # minimal
            return f'''<div style="padding:15px 0;font-size:13px;color:#666;">
                <strong style="color:{KRYSTO_DARK};">{name}</strong>{" | " + title if title else ""} | {company}<br>
                <span style="font-size:12px;">{" | ".join(contact_lines).replace("<br>", " | ")}</span>
            </div>'''
    
    def get_preview_text(self):
        return f"✍️ {self.content.get('name', 'Signature')}"


class AlertBlock(EmailBlock):
    """Bannière d'alerte/notification"""
    BLOCK_TYPE = "alert"
    BLOCK_ICON = "⚠️"
    BLOCK_NAME = "Alerte"
    
    @classmethod
    def get_default_content(cls):
        return {
            "text": "Information importante",
            "type": "info",  # info, success, warning, error, promo
            "icon": "auto",  # auto ou emoji personnalisé
            "style": "banner",  # banner, card, minimal
            "dismissible": False
        }
    
    def to_html(self, context=None):
        c = self.content
        text = c.get('text', '')
        alert_type = c.get('type', 'info')
        icon = c.get('icon', 'auto')
        style = c.get('style', 'banner')
        
        # Couleurs et icônes par type
        type_config = {
            "info": {"bg": "#e3f2fd", "color": "#1565c0", "icon": "ℹ️", "border": "#1565c0"},
            "success": {"bg": "#e8f5e9", "color": "#2e7d32", "icon": "✅", "border": "#2e7d32"},
            "warning": {"bg": "#fff3e0", "color": "#ef6c00", "icon": "⚠️", "border": "#ef6c00"},
            "error": {"bg": "#ffebee", "color": "#c62828", "icon": "❌", "border": "#c62828"},
            "promo": {"bg": f"linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY})", "color": "#ffffff", "icon": "🎉", "border": KRYSTO_PRIMARY}
        }
        
        config = type_config.get(alert_type, type_config["info"])
        display_icon = config["icon"] if icon == "auto" else icon
        
        if style == "banner":
            bg = config["bg"] if alert_type != "promo" else config["bg"]
            return f'''<div style="background:{bg};padding:15px 20px;border-radius:8px;margin:10px 0;">
                <span style="font-size:20px;margin-right:10px;">{display_icon}</span>
                <span style="color:{config["color"]};font-size:15px;font-weight:500;">{text}</span>
            </div>'''
        elif style == "card":
            return f'''<div style="background:white;border-left:4px solid {config["border"]};padding:20px;border-radius:0 8px 8px 0;box-shadow:0 2px 10px rgba(0,0,0,0.08);margin:10px 0;">
                <span style="font-size:24px;display:block;margin-bottom:10px;">{display_icon}</span>
                <span style="color:{config["color"]};font-size:15px;">{text}</span>
            </div>'''
        else:  # minimal
            return f'''<div style="padding:10px 0;border-bottom:2px solid {config["border"]};">
                <span style="color:{config["color"]};font-size:14px;">{display_icon} {text}</span>
            </div>'''
    
    def get_preview_text(self):
        return f"⚠️ {self.content.get('type', 'info').upper()}: {self.content.get('text', '')[:30]}"


class PricingBlock(EmailBlock):
    """Tableau de tarification"""
    BLOCK_TYPE = "pricing"
    BLOCK_ICON = "💎"
    BLOCK_NAME = "Tarif"
    
    @classmethod
    def get_default_content(cls):
        return {
            "name": "Offre Standard",
            "price": "9 900",
            "currency": "XPF",
            "period": "/mois",
            "features": ["Feature 1", "Feature 2", "Feature 3"],
            "cta_text": "Choisir",
            "cta_url": "",
            "highlighted": False,
            "badge": "",
            "style": "card"
        }
    
    def to_html(self, context=None):
        c = self.content
        name = c.get('name', '')
        price = c.get('price', '')
        currency = c.get('currency', 'XPF')
        period = c.get('period', '')
        features = c.get('features', [])
        cta_text = c.get('cta_text', '')
        cta_url = c.get('cta_url', '')
        highlighted = c.get('highlighted', False)
        badge = c.get('badge', '')
        
        bg = f"linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY})" if highlighted else "white"
        text_color = "white" if highlighted else KRYSTO_DARK
        price_color = "white" if highlighted else KRYSTO_PRIMARY
        feature_color = "rgba(255,255,255,0.9)" if highlighted else "#666"
        shadow = "box-shadow:0 10px 40px rgba(109,116,171,0.3);" if highlighted else "box-shadow:0 4px 20px rgba(0,0,0,0.08);"
        
        badge_html = f'<div style="position:absolute;top:-12px;right:20px;background:#ff6b6b;color:white;padding:5px 15px;border-radius:15px;font-size:12px;font-weight:bold;">{badge}</div>' if badge else ""
        
        features_html = "".join([f'<div style="padding:8px 0;color:{feature_color};font-size:14px;">✓ {f}</div>' for f in features])
        
        cta_html = ""
        if cta_text and cta_url:
            btn_bg = "white" if highlighted else f"linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY})"
            btn_color = KRYSTO_PRIMARY if highlighted else "white"
            cta_html = f'<a href="{cta_url}" style="display:block;padding:14px 30px;background:{btn_bg};color:{btn_color};text-decoration:none;border-radius:25px;font-weight:bold;text-align:center;margin-top:20px;">{cta_text}</a>'
        
        return f'''<div style="position:relative;background:{bg};border-radius:20px;padding:30px;text-align:center;{shadow}">
            {badge_html}
            <h3 style="margin:0 0 20px 0;color:{text_color};font-size:20px;">{name}</h3>
            <div style="margin:20px 0;">
                <span style="font-size:48px;font-weight:bold;color:{price_color};">{price}</span>
                <span style="font-size:16px;color:{feature_color};">{currency}{period}</span>
            </div>
            <div style="border-top:1px solid {"rgba(255,255,255,0.2)" if highlighted else "#e0e0e0"};padding-top:20px;text-align:left;">
                {features_html}
            </div>
            {cta_html}
        </div>'''
    
    def get_preview_text(self):
        return f"💎 {self.content.get('name', 'Tarif')}: {self.content.get('price', '')} {self.content.get('currency', '')}"


class TimelineBlock(EmailBlock):
    """Timeline / Étapes"""
    BLOCK_TYPE = "timeline"
    BLOCK_ICON = "📅"
    BLOCK_NAME = "Timeline"
    
    @classmethod
    def get_default_content(cls):
        return {
            "items": [
                {"title": "Étape 1", "description": "Description", "icon": "1"},
                {"title": "Étape 2", "description": "Description", "icon": "2"},
                {"title": "Étape 3", "description": "Description", "icon": "3"}
            ],
            "style": "vertical",  # vertical, horizontal
            "accent_color": KRYSTO_PRIMARY
        }
    
    def to_html(self, context=None):
        c = self.content
        items = c.get('items', [])
        style = c.get('style', 'vertical')
        accent = c.get('accent_color', KRYSTO_PRIMARY)
        
        if not items:
            return ""
        
        if style == "horizontal":
            items_html = ""
            width = f"{100 // len(items)}%"
            for item in items:
                items_html += f'''<td style="width:{width};text-align:center;padding:10px;vertical-align:top;">
                    <div style="width:50px;height:50px;background:linear-gradient(135deg,{accent},{KRYSTO_SECONDARY});border-radius:50%;color:white;font-weight:bold;font-size:20px;line-height:50px;margin:0 auto 15px;">{item.get("icon", "•")}</div>
                    <strong style="color:{KRYSTO_DARK};font-size:14px;">{item.get("title", "")}</strong>
                    <p style="margin:8px 0 0 0;color:#666;font-size:12px;">{item.get("description", "")}</p>
                </td>'''
            return f'<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>{items_html}</tr></table>'
        else:  # vertical
            items_html = ""
            for i, item in enumerate(items):
                line = f'<div style="position:absolute;left:24px;top:50px;bottom:-20px;width:2px;background:{accent};"></div>' if i < len(items) - 1 else ""
                items_html += f'''<div style="position:relative;padding-left:70px;padding-bottom:30px;">
                    <div style="position:absolute;left:0;top:0;width:50px;height:50px;background:linear-gradient(135deg,{accent},{KRYSTO_SECONDARY});border-radius:50%;color:white;font-weight:bold;font-size:18px;text-align:center;line-height:50px;">{item.get("icon", "•")}</div>
                    {line}
                    <strong style="color:{KRYSTO_DARK};font-size:16px;display:block;margin-bottom:5px;">{item.get("title", "")}</strong>
                    <p style="margin:0;color:#666;font-size:14px;line-height:1.5;">{item.get("description", "")}</p>
                </div>'''
            return f'<div style="padding:20px 10px;">{items_html}</div>'
    
    def get_preview_text(self):
        return f"📅 Timeline: {len(self.content.get('items', []))} étapes"


class TeamBlock(EmailBlock):
    """Profil équipe / personne"""
    BLOCK_TYPE = "team"
    BLOCK_ICON = "👤"
    BLOCK_NAME = "Profil"
    
    @classmethod
    def get_default_content(cls):
        return {
            "photo_url": "",
            "name": "Nom Prénom",
            "title": "Fonction",
            "bio": "",
            "email": "",
            "phone": "",
            "social": {},
            "style": "card"  # card, horizontal, minimal
        }
    
    def to_html(self, context=None):
        c = self.content
        photo_url = c.get('photo_url', '')
        name = c.get('name', '')
        title = c.get('title', '')
        bio = c.get('bio', '')
        email = c.get('email', '')
        phone = c.get('phone', '')
        style = c.get('style', 'card')
        
        photo_html = f'<img src="{photo_url}" style="width:100px;height:100px;border-radius:50%;object-fit:cover;">' if photo_url else f'<div style="width:100px;height:100px;border-radius:50%;background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});display:flex;align-items:center;justify-content:center;font-size:40px;color:white;">👤</div>'
        
        contact_html = ""
        if email or phone:
            contacts = []
            if email: contacts.append(f'<a href="mailto:{email}" style="color:{KRYSTO_PRIMARY};text-decoration:none;">✉️ {email}</a>')
            if phone: contacts.append(f'📞 {phone}')
            contact_html = f'<div style="margin-top:15px;font-size:13px;">{" | ".join(contacts)}</div>'
        
        bio_html = f'<p style="margin:15px 0 0 0;color:#666;font-size:14px;line-height:1.6;">{bio}</p>' if bio else ""
        
        if style == "card":
            return f'''<div style="background:white;border-radius:15px;padding:30px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
                <div style="margin-bottom:20px;">{photo_html}</div>
                <h3 style="margin:0;color:{KRYSTO_DARK};font-size:20px;">{name}</h3>
                <p style="margin:5px 0 0 0;color:{KRYSTO_PRIMARY};font-size:14px;font-weight:500;">{title}</p>
                {bio_html}{contact_html}
            </div>'''
        elif style == "horizontal":
            return f'''<div style="display:flex;align-items:center;padding:20px;background:#f8f9fa;border-radius:12px;">
                <div style="margin-right:20px;">{photo_html}</div>
                <div>
                    <h3 style="margin:0;color:{KRYSTO_DARK};font-size:18px;">{name}</h3>
                    <p style="margin:5px 0;color:{KRYSTO_PRIMARY};font-size:13px;">{title}</p>
                    {bio_html}{contact_html}
                </div>
            </div>'''
        else:  # minimal
            return f'''<div style="padding:15px 0;border-bottom:1px solid #e0e0e0;">
                <strong style="color:{KRYSTO_DARK};">{name}</strong> - <span style="color:{KRYSTO_PRIMARY};">{title}</span>
                {bio_html}
            </div>'''
    
    def get_preview_text(self):
        return f"👤 {self.content.get('name', 'Profil')}"


class RatingBlock(EmailBlock):
    """Affichage note/étoiles"""
    BLOCK_TYPE = "rating"
    BLOCK_ICON = "⭐"
    BLOCK_NAME = "Note"
    
    @classmethod
    def get_default_content(cls):
        return {
            "rating": 5,
            "max_rating": 5,
            "text": "",
            "style": "stars",  # stars, numeric, both
            "size": "medium",  # small, medium, large
            "color": "#ffc107"
        }
    
    def to_html(self, context=None):
        c = self.content
        rating = c.get('rating', 5)
        max_rating = c.get('max_rating', 5)
        text = c.get('text', '')
        style = c.get('style', 'stars')
        size = c.get('size', 'medium')
        color = c.get('color', '#ffc107')
        
        sizes = {"small": 16, "medium": 24, "large": 36}
        font_size = sizes.get(size, 24)
        
        stars_html = ""
        for i in range(max_rating):
            star = "★" if i < rating else "☆"
            stars_html += f'<span style="color:{color if i < rating else "#ddd"};font-size:{font_size}px;">{star}</span>'
        
        text_html = f'<span style="color:#666;font-size:{font_size * 0.6}px;margin-left:10px;">{text}</span>' if text else ""
        
        if style == "numeric":
            return f'''<div style="text-align:center;padding:15px;">
                <span style="font-size:{font_size * 1.5}px;font-weight:bold;color:{KRYSTO_DARK};">{rating}</span>
                <span style="color:#666;font-size:{font_size * 0.7}px;">/{max_rating}</span>
                {text_html}
            </div>'''
        elif style == "both":
            return f'''<div style="text-align:center;padding:15px;">
                <div>{stars_html}</div>
                <div style="margin-top:8px;">
                    <span style="font-size:{font_size}px;font-weight:bold;color:{KRYSTO_DARK};">{rating}/{max_rating}</span>
                    {text_html}
                </div>
            </div>'''
        else:  # stars
            return f'<div style="text-align:center;padding:15px;">{stars_html}{text_html}</div>'
    
    def get_preview_text(self):
        return f"⭐ {'★' * self.content.get('rating', 5)}{'☆' * (self.content.get('max_rating', 5) - self.content.get('rating', 5))}"


class FeatureBoxBlock(EmailBlock):
    """Boîtes de fonctionnalités avec icônes"""
    BLOCK_TYPE = "feature_box"
    BLOCK_ICON = "✨"
    BLOCK_NAME = "Features"
    
    @classmethod
    def get_default_content(cls):
        return {
            "features": [
                {"icon": "🚀", "title": "Rapide", "description": "Description courte"},
                {"icon": "🔒", "title": "Sécurisé", "description": "Description courte"},
                {"icon": "💡", "title": "Innovant", "description": "Description courte"}
            ],
            "columns": 3,
            "style": "cards"  # cards, minimal, icons
        }
    
    def to_html(self, context=None):
        c = self.content
        features = c.get('features', [])
        columns = c.get('columns', 3)
        style = c.get('style', 'cards')
        
        if not features:
            return ""
        
        width = f"{100 // columns - 2}%"
        
        features_html = ""
        for f in features:
            icon = f.get('icon', '✨')
            title = f.get('title', '')
            desc = f.get('description', '')
            
            if style == "cards":
                features_html += f'''<div style="display:inline-block;width:{width};padding:10px;vertical-align:top;">
                    <div style="background:white;border-radius:15px;padding:25px;text-align:center;box-shadow:0 4px 15px rgba(0,0,0,0.08);height:100%;">
                        <div style="font-size:40px;margin-bottom:15px;">{icon}</div>
                        <h4 style="margin:0 0 10px 0;color:{KRYSTO_DARK};font-size:16px;">{title}</h4>
                        <p style="margin:0;color:#666;font-size:13px;line-height:1.5;">{desc}</p>
                    </div>
                </div>'''
            elif style == "minimal":
                features_html += f'''<div style="display:inline-block;width:{width};padding:15px;vertical-align:top;text-align:center;">
                    <span style="font-size:30px;">{icon}</span>
                    <h4 style="margin:10px 0 5px 0;color:{KRYSTO_DARK};font-size:14px;">{title}</h4>
                    <p style="margin:0;color:#666;font-size:12px;">{desc}</p>
                </div>'''
            else:  # icons
                features_html += f'''<div style="display:inline-block;width:{width};padding:10px;vertical-align:top;">
                    <div style="display:flex;align-items:flex-start;">
                        <div style="width:50px;height:50px;background:linear-gradient(135deg,{KRYSTO_PRIMARY}22,{KRYSTO_SECONDARY}22);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;margin-right:15px;">{icon}</div>
                        <div>
                            <h4 style="margin:0 0 5px 0;color:{KRYSTO_DARK};font-size:15px;">{title}</h4>
                            <p style="margin:0;color:#666;font-size:13px;">{desc}</p>
                        </div>
                    </div>
                </div>'''
        
        return f'<div style="text-align:center;font-size:0;">{features_html}</div>'
    
    def get_preview_text(self):
        return f"✨ {len(self.content.get('features', []))} features"


class TableBlock(EmailBlock):
    """Tableau simple"""
    BLOCK_TYPE = "table"
    BLOCK_ICON = "📊"
    BLOCK_NAME = "Tableau"
    
    @classmethod
    def get_default_content(cls):
        return {
            "headers": ["Colonne 1", "Colonne 2", "Colonne 3"],
            "rows": [["Valeur 1", "Valeur 2", "Valeur 3"]],
            "style": "striped",  # striped, bordered, minimal
            "header_bg": KRYSTO_PRIMARY,
            "header_color": "#ffffff"
        }
    
    def to_html(self, context=None):
        c = self.content
        headers = c.get('headers', [])
        rows = c.get('rows', [])
        style = c.get('style', 'striped')
        header_bg = c.get('header_bg', KRYSTO_PRIMARY)
        header_color = c.get('header_color', '#ffffff')
        
        if not headers and not rows:
            return ""
        
        border = "1px solid #e0e0e0" if style == "bordered" else "none"
        
        # Headers
        headers_html = ""
        if headers:
            cells = "".join([f'<th style="padding:12px 15px;background:{header_bg};color:{header_color};font-weight:bold;text-align:left;border:{border};">{h}</th>' for h in headers])
            headers_html = f'<tr>{cells}</tr>'
        
        # Rows
        rows_html = ""
        for i, row in enumerate(rows):
            bg = "#f8f9fa" if style == "striped" and i % 2 == 0 else "white"
            cells = "".join([f'<td style="padding:12px 15px;background:{bg};color:{KRYSTO_DARK};border:{border};">{cell}</td>' for cell in row])
            rows_html += f'<tr>{cells}</tr>'
        
        return f'''<table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse:collapse;border-radius:8px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.05);">
            {headers_html}{rows_html}
        </table>'''
    
    def get_preview_text(self):
        return f"📊 Tableau: {len(self.content.get('rows', []))} lignes"


class ProgressBlock(EmailBlock):
    """Barre de progression"""
    BLOCK_TYPE = "progress"
    BLOCK_ICON = "📶"
    BLOCK_NAME = "Progression"
    
    @classmethod
    def get_default_content(cls):
        return {
            "items": [{"label": "Objectif", "value": 75, "max": 100}],
            "style": "bar",  # bar, circle
            "show_percentage": True,
            "color": KRYSTO_PRIMARY
        }
    
    def to_html(self, context=None):
        c = self.content
        items = c.get('items', [])
        style = c.get('style', 'bar')
        show_pct = c.get('show_percentage', True)
        color = c.get('color', KRYSTO_PRIMARY)
        
        if not items:
            return ""
        
        items_html = ""
        for item in items:
            label = item.get('label', '')
            value = item.get('value', 0)
            max_val = item.get('max', 100)
            pct = min(100, int((value / max_val) * 100)) if max_val > 0 else 0
            
            pct_text = f'<span style="font-weight:bold;color:{KRYSTO_DARK};">{pct}%</span>' if show_pct else ""
            
            items_html += f'''<div style="margin-bottom:15px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                    <span style="color:{KRYSTO_DARK};font-size:14px;">{label}</span>
                    {pct_text}
                </div>
                <div style="background:#e0e0e0;border-radius:10px;height:12px;overflow:hidden;">
                    <div style="background:linear-gradient(90deg,{color},{KRYSTO_SECONDARY});width:{pct}%;height:100%;border-radius:10px;"></div>
                </div>
            </div>'''
        
        return f'<div style="padding:15px;">{items_html}</div>'
    
    def get_preview_text(self):
        return f"📶 {len(self.content.get('items', []))} barre(s)"


class SeparatorTextBlock(EmailBlock):
    """Séparateur avec texte"""
    BLOCK_TYPE = "separator_text"
    BLOCK_ICON = "➖"
    BLOCK_NAME = "Séparateur texte"
    
    @classmethod
    def get_default_content(cls):
        return {
            "text": "ou",
            "style": "line",  # line, dots, gradient
            "color": "#e0e0e0",
            "text_color": "#888888"
        }
    
    def to_html(self, context=None):
        c = self.content
        text = c.get('text', '')
        style = c.get('style', 'line')
        color = c.get('color', '#e0e0e0')
        text_color = c.get('text_color', '#888888')
        
        if style == "gradient":
            line = f'linear-gradient(90deg, transparent, {color}, transparent)'
        elif style == "dots":
            line = f'repeating-linear-gradient(90deg, {color}, {color} 4px, transparent 4px, transparent 8px)'
        else:
            line = color
        
        return f'''<div style="display:flex;align-items:center;padding:20px 0;">
            <div style="flex:1;height:1px;background:{line};"></div>
            <span style="padding:0 20px;color:{text_color};font-size:14px;">{text}</span>
            <div style="flex:1;height:1px;background:{line};"></div>
        </div>'''
    
    def get_preview_text(self):
        return f"➖ {self.content.get('text', 'ou')}"


class BeforeAfterBlock(EmailBlock):
    """Comparaison avant/après"""
    BLOCK_TYPE = "before_after"
    BLOCK_ICON = "🔄"
    BLOCK_NAME = "Avant/Après"
    
    @classmethod
    def get_default_content(cls):
        return {
            "before_image": "",
            "after_image": "",
            "before_label": "Avant",
            "after_label": "Après",
            "style": "side_by_side",  # side_by_side, stacked
            "border_radius": 12
        }
    
    def to_html(self, context=None):
        c = self.content
        before_img = c.get('before_image', '')
        after_img = c.get('after_image', '')
        before_label = c.get('before_label', 'Avant')
        after_label = c.get('after_label', 'Après')
        style = c.get('style', 'side_by_side')
        radius = c.get('border_radius', 12)
        
        if style == "side_by_side":
            return f'''<div style="display:flex;gap:15px;padding:10px;">
                <div style="flex:1;text-align:center;">
                    <p style="margin:0 0 10px;font-weight:bold;color:#888;">{before_label}</p>
                    <img src="{before_img}" style="width:100%;border-radius:{radius}px;border:3px solid #ff6b6b;">
                </div>
                <div style="flex:1;text-align:center;">
                    <p style="margin:0 0 10px;font-weight:bold;color:#888;">{after_label}</p>
                    <img src="{after_img}" style="width:100%;border-radius:{radius}px;border:3px solid {KRYSTO_SECONDARY};">
                </div>
            </div>'''
        else:
            return f'''<div style="padding:10px;">
                <div style="margin-bottom:20px;text-align:center;">
                    <p style="margin:0 0 10px;font-weight:bold;color:#ff6b6b;">{before_label}</p>
                    <img src="{before_img}" style="width:100%;max-width:400px;border-radius:{radius}px;">
                </div>
                <div style="text-align:center;font-size:30px;color:{KRYSTO_PRIMARY};">⬇️</div>
                <div style="margin-top:20px;text-align:center;">
                    <p style="margin:0 0 10px;font-weight:bold;color:{KRYSTO_SECONDARY};">{after_label}</p>
                    <img src="{after_img}" style="width:100%;max-width:400px;border-radius:{radius}px;">
                </div>
            </div>'''
    
    def get_preview_text(self):
        return f"🔄 Avant/Après"


class IconRowBlock(EmailBlock):
    """Ligne d'icônes avec texte"""
    BLOCK_TYPE = "icon_row"
    BLOCK_ICON = "🎯"
    BLOCK_NAME = "Icônes en ligne"
    
    @classmethod
    def get_default_content(cls):
        return {
            "items": [
                {"icon": "🚚", "text": "Livraison gratuite"},
                {"icon": "🔒", "text": "Paiement sécurisé"},
                {"icon": "↩️", "text": "Retour facile"},
            ],
            "style": "inline",  # inline, badges
            "icon_size": 24,
            "color": KRYSTO_PRIMARY
        }
    
    def to_html(self, context=None):
        c = self.content
        items = c.get('items', [])
        style = c.get('style', 'inline')
        icon_size = c.get('icon_size', 24)
        color = c.get('color', KRYSTO_PRIMARY)
        
        if not items:
            return ""
        
        items_html = ""
        for item in items:
            icon = item.get('icon', '✓')
            text = item.get('text', '')
            
            if style == "badges":
                items_html += f'''<div style="display:inline-block;background:{color}15;padding:10px 20px;border-radius:25px;margin:5px;">
                    <span style="font-size:{icon_size}px;margin-right:8px;">{icon}</span>
                    <span style="color:{KRYSTO_DARK};font-size:14px;">{text}</span>
                </div>'''
            else:
                items_html += f'''<div style="display:inline-block;text-align:center;padding:15px 25px;">
                    <div style="font-size:{icon_size}px;margin-bottom:8px;">{icon}</div>
                    <div style="color:{KRYSTO_DARK};font-size:13px;">{text}</div>
                </div>'''
        
        return f'<div style="text-align:center;padding:15px 0;">{items_html}</div>'
    
    def get_preview_text(self):
        return f"🎯 {len(self.content.get('items', []))} icônes"


class CalloutBlock(EmailBlock):
    """Box mise en avant / Callout"""
    BLOCK_TYPE = "callout"
    BLOCK_ICON = "💡"
    BLOCK_NAME = "Callout"
    
    @classmethod
    def get_default_content(cls):
        return {
            "icon": "💡",
            "title": "Le saviez-vous ?",
            "text": "Contenu informatif...",
            "style": "tip",  # tip, warning, success, info, quote
            "show_icon": True
        }
    
    def to_html(self, context=None):
        c = self.content
        icon = c.get('icon', '💡')
        title = c.get('title', '')
        text = c.get('text', '')
        style = c.get('style', 'tip')
        show_icon = c.get('show_icon', True)
        
        styles = {
            "tip": {"bg": "#fff8e1", "border": "#ffc107", "icon": "💡"},
            "warning": {"bg": "#fff3e0", "border": "#ff9800", "icon": "⚠️"},
            "success": {"bg": "#e8f5e9", "border": "#4caf50", "icon": "✅"},
            "info": {"bg": "#e3f2fd", "border": "#2196f3", "icon": "ℹ️"},
            "quote": {"bg": "#f3e5f5", "border": "#9c27b0", "icon": "💬"},
        }
        
        s = styles.get(style, styles["tip"])
        display_icon = icon if icon != "auto" else s["icon"]
        
        icon_html = f'<span style="font-size:28px;margin-right:15px;">{display_icon}</span>' if show_icon else ""
        title_html = f'<strong style="color:{KRYSTO_DARK};font-size:16px;display:block;margin-bottom:8px;">{title}</strong>' if title else ""
        
        return f'''<div style="background:{s["bg"]};border-left:4px solid {s["border"]};padding:20px;border-radius:0 12px 12px 0;margin:15px 0;">
            <div style="display:flex;align-items:flex-start;">
                {icon_html}
                <div>
                    {title_html}
                    <p style="margin:0;color:#666;font-size:14px;line-height:1.6;">{text}</p>
                </div>
            </div>
        </div>'''
    
    def get_preview_text(self):
        return f"💡 {self.content.get('title', 'Callout')}"


class ChecklistBlock(EmailBlock):
    """Liste de vérification avec cases"""
    BLOCK_TYPE = "checklist"
    BLOCK_ICON = "☑️"
    BLOCK_NAME = "Checklist"
    
    @classmethod
    def get_default_content(cls):
        return {
            "title": "",
            "items": [
                {"text": "Élément 1", "checked": True},
                {"text": "Élément 2", "checked": True},
                {"text": "Élément 3", "checked": False},
            ],
            "style": "modern",  # modern, simple, strikethrough
            "checked_color": KRYSTO_SECONDARY,
            "unchecked_color": "#ccc"
        }
    
    def to_html(self, context=None):
        c = self.content
        title = c.get('title', '')
        items = c.get('items', [])
        style = c.get('style', 'modern')
        checked_color = c.get('checked_color', KRYSTO_SECONDARY)
        unchecked_color = c.get('unchecked_color', '#ccc')
        
        title_html = f'<h3 style="margin:0 0 15px;color:{KRYSTO_DARK};">{title}</h3>' if title else ""
        
        items_html = ""
        for item in items:
            text = item.get('text', '')
            checked = item.get('checked', False)
            
            if style == "modern":
                check_icon = f'<div style="width:24px;height:24px;background:{checked_color if checked else "transparent"};border:2px solid {checked_color if checked else unchecked_color};border-radius:50%;display:inline-flex;align-items:center;justify-content:center;margin-right:12px;"><span style="color:white;font-size:14px;">{"✓" if checked else ""}</span></div>'
                text_style = f'color:{KRYSTO_DARK};' if checked else f'color:#999;'
            elif style == "strikethrough":
                check_icon = f'<span style="margin-right:10px;">{("✅" if checked else "⬜")}</span>'
                text_style = f'color:#999;text-decoration:line-through;' if checked else f'color:{KRYSTO_DARK};'
            else:
                check_icon = f'<span style="color:{checked_color if checked else unchecked_color};margin-right:10px;">{"☑️" if checked else "☐"}</span>'
                text_style = f'color:{KRYSTO_DARK};'
            
            items_html += f'<div style="padding:10px 0;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;">{check_icon}<span style="{text_style}font-size:15px;">{text}</span></div>'
        
        return f'<div style="background:#fafafa;padding:20px;border-radius:12px;">{title_html}{items_html}</div>'
    
    def get_preview_text(self):
        items = self.content.get('items', [])
        checked = sum(1 for i in items if i.get('checked'))
        return f"☑️ {checked}/{len(items)} complété"


class ContactBlock(EmailBlock):
    """Bloc contact complet"""
    BLOCK_TYPE = "contact"
    BLOCK_ICON = "📞"
    BLOCK_NAME = "Contact"
    
    @classmethod
    def get_default_content(cls):
        return {
            "title": "Contactez-nous",
            "email": COMPANY_EMAIL,
            "phone": COMPANY_PHONE,
            "address": COMPANY_ADDRESS,
            "website": COMPANY_WEBSITE,
            "hours": "Lun-Ven: 8h-17h",
            "style": "card",  # card, inline, minimal
            "show_icons": True
        }
    
    def to_html(self, context=None):
        c = self.content
        title = c.get('title', '')
        email = c.get('email', '')
        phone = c.get('phone', '')
        address = c.get('address', '')
        website = c.get('website', '')
        hours = c.get('hours', '')
        style = c.get('style', 'card')
        
        items = []
        if email: items.append(f'<a href="mailto:{email}" style="color:{KRYSTO_PRIMARY};text-decoration:none;">✉️ {email}</a>')
        if phone: items.append(f'<a href="tel:{phone}" style="color:{KRYSTO_PRIMARY};text-decoration:none;">📞 {phone}</a>')
        if address: items.append(f'📍 {address}')
        if website: items.append(f'<a href="https://{website}" style="color:{KRYSTO_PRIMARY};text-decoration:none;">🌐 {website}</a>')
        if hours: items.append(f'🕐 {hours}')
        
        if style == "card":
            items_html = "".join(f'<div style="padding:12px 0;border-bottom:1px solid #eee;font-size:14px;">{i}</div>' for i in items)
            title_html = f'<h3 style="margin:0 0 15px;color:{KRYSTO_DARK};font-size:18px;">{title}</h3>' if title else ""
            return f'''<div style="background:linear-gradient(135deg,{KRYSTO_PRIMARY}08,{KRYSTO_SECONDARY}08);border:1px solid #e0e0e0;border-radius:15px;padding:25px;">
                {title_html}{items_html}
            </div>'''
        elif style == "inline":
            items_html = " • ".join(items)
            return f'<div style="text-align:center;padding:20px;background:#f8f9fa;border-radius:10px;font-size:14px;">{items_html}</div>'
        else:
            items_html = "<br>".join(items)
            return f'<div style="padding:15px;font-size:14px;line-height:2;">{items_html}</div>'
    
    def get_preview_text(self):
        return f"📞 Contact"


class BannerBlock(EmailBlock):
    """Bannière promotionnelle"""
    BLOCK_TYPE = "banner"
    BLOCK_ICON = "🎪"
    BLOCK_NAME = "Bannière"
    
    @classmethod
    def get_default_content(cls):
        return {
            "text": "🎉 Offre spéciale !",
            "subtext": "Profitez de -20% sur tout le site",
            "style": "gradient",  # gradient, solid, outline, animated
            "color_1": KRYSTO_PRIMARY,
            "color_2": KRYSTO_SECONDARY,
            "text_color": "#ffffff",
            "size": "medium"  # small, medium, large
        }
    
    def to_html(self, context=None):
        c = self.content
        text = c.get('text', '')
        subtext = c.get('subtext', '')
        style = c.get('style', 'gradient')
        color_1 = c.get('color_1', KRYSTO_PRIMARY)
        color_2 = c.get('color_2', KRYSTO_SECONDARY)
        text_color = c.get('text_color', '#ffffff')
        size = c.get('size', 'medium')
        
        sizes = {"small": (14, 12, 15), "medium": (20, 14, 25), "large": (28, 16, 35)}
        text_size, sub_size, padding = sizes.get(size, sizes["medium"])
        
        if style == "gradient":
            bg = f"linear-gradient(135deg, {color_1}, {color_2})"
        elif style == "outline":
            bg = "transparent"
            text_color = color_1
        elif style == "animated":
            bg = f"linear-gradient(90deg, {color_1}, {color_2}, {color_1})"
        else:
            bg = color_1
        
        border = f"border:3px solid {color_1};" if style == "outline" else ""
        subtext_html = f'<p style="margin:8px 0 0;font-size:{sub_size}px;opacity:0.9;">{subtext}</p>' if subtext else ""
        
        return f'''<div style="background:{bg};color:{text_color};text-align:center;padding:{padding}px;border-radius:12px;{border}">
            <p style="margin:0;font-size:{text_size}px;font-weight:bold;">{text}</p>
            {subtext_html}
        </div>'''
    
    def get_preview_text(self):
        return f"🎪 {self.content.get('text', 'Bannière')[:25]}"


class AvatarGroupBlock(EmailBlock):
    """Groupe d'avatars (témoignages, équipe)"""
    BLOCK_TYPE = "avatar_group"
    BLOCK_ICON = "👥"
    BLOCK_NAME = "Avatars"
    
    @classmethod
    def get_default_content(cls):
        return {
            "avatars": [
                {"image": "", "name": "Alice"},
                {"image": "", "name": "Bob"},
                {"image": "", "name": "Charlie"},
            ],
            "text": "+500 clients satisfaits",
            "style": "overlap",  # overlap, grid, list
            "size": 50
        }
    
    def to_html(self, context=None):
        c = self.content
        avatars = c.get('avatars', [])
        text = c.get('text', '')
        style = c.get('style', 'overlap')
        size = c.get('size', 50)
        
        avatars_html = ""
        for i, av in enumerate(avatars[:5]):
            img = av.get('image', '')
            name = av.get('name', '')
            initials = name[:2].upper() if name else "?"
            
            if img:
                avatar = f'<img src="{img}" style="width:{size}px;height:{size}px;border-radius:50%;object-fit:cover;border:3px solid white;">'
            else:
                colors = [KRYSTO_PRIMARY, KRYSTO_SECONDARY, "#ff6b6b", "#4ecdc4", "#45b7d1"]
                bg = colors[i % len(colors)]
                avatar = f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{bg};color:white;display:inline-flex;align-items:center;justify-content:center;font-weight:bold;font-size:{size//3}px;border:3px solid white;">{initials}</div>'
            
            margin = f"margin-left:-{size//3}px;" if style == "overlap" and i > 0 else "margin:5px;"
            avatars_html += f'<div style="display:inline-block;{margin}">{avatar}</div>'
        
        text_html = f'<span style="margin-left:15px;color:{KRYSTO_DARK};font-size:14px;font-weight:500;">{text}</span>' if text else ""
        
        return f'<div style="text-align:center;padding:20px;display:flex;align-items:center;justify-content:center;">{avatars_html}{text_html}</div>'
    
    def get_preview_text(self):
        return f"👥 {len(self.content.get('avatars', []))} avatars"


class GradientTextBlock(EmailBlock):
    """Texte avec effet dégradé"""
    BLOCK_TYPE = "gradient_text"
    BLOCK_ICON = "🌈"
    BLOCK_NAME = "Texte dégradé"
    
    @classmethod
    def get_default_content(cls):
        return {
            "text": "Texte Stylisé",
            "color_1": KRYSTO_PRIMARY,
            "color_2": KRYSTO_SECONDARY,
            "font_size": 36,
            "font_weight": "bold",
            "align": "center"
        }
    
    def to_html(self, context=None):
        c = self.content
        text = c.get('text', '')
        color_1 = c.get('color_1', KRYSTO_PRIMARY)
        color_2 = c.get('color_2', KRYSTO_SECONDARY)
        font_size = c.get('font_size', 36)
        font_weight = c.get('font_weight', 'bold')
        align = c.get('align', 'center')
        
        # Email clients don't support background-clip, so use solid gradient background with text
        return f'''<div style="text-align:{align};padding:20px;">
            <span style="font-size:{font_size}px;font-weight:{font_weight};background:linear-gradient(135deg,{color_1},{color_2});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">{text}</span>
        </div>'''
    
    def get_preview_text(self):
        return f"🌈 {self.content.get('text', '')[:20]}"


class LogoCloudBlock(EmailBlock):
    """Logos partenaires / marques"""
    BLOCK_TYPE = "logo_cloud"
    BLOCK_ICON = "🏢"
    BLOCK_NAME = "Logos"
    
    @classmethod
    def get_default_content(cls):
        return {
            "title": "Ils nous font confiance",
            "logos": [
                {"url": "", "name": "Partenaire 1"},
                {"url": "", "name": "Partenaire 2"},
                {"url": "", "name": "Partenaire 3"},
            ],
            "columns": 3,
            "grayscale": True,
            "logo_height": 50
        }
    
    def to_html(self, context=None):
        c = self.content
        title = c.get('title', '')
        logos = c.get('logos', [])
        columns = c.get('columns', 3)
        grayscale = c.get('grayscale', True)
        logo_height = c.get('logo_height', 50)
        
        title_html = f'<p style="text-align:center;color:#888;font-size:14px;margin-bottom:20px;">{title}</p>' if title else ""
        
        filter_style = "filter:grayscale(100%);opacity:0.7;" if grayscale else ""
        width = f"{100 // columns - 2}%"
        
        logos_html = ""
        for logo in logos:
            url = logo.get('url', '')
            name = logo.get('name', '')
            if url:
                logos_html += f'<div style="display:inline-block;width:{width};text-align:center;padding:15px;vertical-align:middle;"><img src="{url}" alt="{name}" style="height:{logo_height}px;max-width:100%;{filter_style}"></div>'
            else:
                logos_html += f'<div style="display:inline-block;width:{width};text-align:center;padding:15px;vertical-align:middle;"><span style="color:#ccc;font-size:12px;">{name}</span></div>'
        
        return f'<div style="padding:20px 10px;background:#fafafa;border-radius:12px;">{title_html}<div style="text-align:center;">{logos_html}</div></div>'
    
    def get_preview_text(self):
        return f"🏢 {len(self.content.get('logos', []))} logos"


class NumberHighlightBlock(EmailBlock):
    """Gros chiffre mis en avant"""
    BLOCK_TYPE = "number_highlight"
    BLOCK_ICON = "🔢"
    BLOCK_NAME = "Chiffre clé"
    
    @classmethod
    def get_default_content(cls):
        return {
            "number": "100",
            "suffix": "+",
            "prefix": "",
            "label": "Clients satisfaits",
            "style": "gradient",  # gradient, solid, outline
            "color": KRYSTO_PRIMARY
        }
    
    def to_html(self, context=None):
        c = self.content
        number = c.get('number', '')
        suffix = c.get('suffix', '')
        prefix = c.get('prefix', '')
        label = c.get('label', '')
        style = c.get('style', 'gradient')
        color = c.get('color', KRYSTO_PRIMARY)
        
        if style == "gradient":
            number_style = f"background:linear-gradient(135deg,{color},{KRYSTO_SECONDARY});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;"
        elif style == "outline":
            number_style = f"color:transparent;-webkit-text-stroke:3px {color};"
        else:
            number_style = f"color:{color};"
        
        return f'''<div style="text-align:center;padding:30px;">
            <div style="font-size:72px;font-weight:bold;{number_style}line-height:1;">
                {prefix}{number}{suffix}
            </div>
            <p style="margin:15px 0 0;color:#666;font-size:18px;">{label}</p>
        </div>'''
    
    def get_preview_text(self):
        c = self.content
        return f"🔢 {c.get('prefix', '')}{c.get('number', '')}{c.get('suffix', '')}"


class DividerIconBlock(EmailBlock):
    """Séparateur avec icône centrale"""
    BLOCK_TYPE = "divider_icon"
    BLOCK_ICON = "✦"
    BLOCK_NAME = "Séparateur icône"
    
    @classmethod
    def get_default_content(cls):
        return {
            "icon": "✦",
            "line_style": "solid",  # solid, dashed, dots
            "color": "#e0e0e0",
            "icon_color": KRYSTO_PRIMARY,
            "icon_size": 24
        }
    
    def to_html(self, context=None):
        c = self.content
        icon = c.get('icon', '✦')
        line_style = c.get('line_style', 'solid')
        color = c.get('color', '#e0e0e0')
        icon_color = c.get('icon_color', KRYSTO_PRIMARY)
        icon_size = c.get('icon_size', 24)
        
        if line_style == "dashed":
            border = f"border-top:2px dashed {color};"
        elif line_style == "dots":
            border = f"border-top:3px dotted {color};"
        else:
            border = f"border-top:1px solid {color};"
        
        return f'''<div style="display:flex;align-items:center;padding:20px 0;">
            <div style="flex:1;{border}"></div>
            <span style="padding:0 20px;font-size:{icon_size}px;color:{icon_color};">{icon}</span>
            <div style="flex:1;{border}"></div>
        </div>'''
    
    def get_preview_text(self):
        return f"✦ Séparateur {self.content.get('icon', '✦')}"


class QRCodeBlock(EmailBlock):
    """QR Code avec texte descriptif"""
    BLOCK_TYPE = "qr_code"
    BLOCK_ICON = "📱"
    BLOCK_NAME = "QR Code"
    
    @classmethod
    def get_default_content(cls):
        return {
            "url": f"https://{COMPANY_WEBSITE}",
            "size": 150,
            "label": "Scannez pour accéder",
            "style": "centered"  # centered, left, right
        }
    
    def to_html(self, context=None):
        c = self.content
        url = c.get('url', '') or f"https://{COMPANY_WEBSITE}"
        size = c.get('size', 150) or 150
        label = c.get('label', '')
        style = c.get('style', 'centered')
        
        # S'assurer que l'URL est valide
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Encoder l'URL pour l'API - utiliser quote_plus pour meilleure compatibilité
        encoded_url = urllib.parse.quote_plus(url)
        
        # API QR Server (gratuite, fiable, pas de limite)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}&format=png&margin=10"
        
        align = {"centered": "center", "left": "left", "right": "right"}.get(style, "center")
        label_html = f'<p style="margin:10px 0 0;color:#666;font-size:13px;">{label}</p>' if label else ""
        
        return f'''<div style="text-align:{align};padding:20px;">
            <img src="{qr_url}" alt="QR Code" width="{size}" height="{size}" style="border-radius:8px;border:1px solid #eee;">
            {label_html}
        </div>'''
    
    def get_preview_text(self):
        url = self.content.get('url', '')[:30]
        return f"📱 QR: {url}..."


class FaqBlock(EmailBlock):
    """FAQ avec questions/réponses"""
    BLOCK_TYPE = "faq"
    BLOCK_ICON = "❓"
    BLOCK_NAME = "FAQ"
    
    @classmethod
    def get_default_content(cls):
        return {
            "title": "Questions fréquentes",
            "items": [
                {"question": "Question 1 ?", "answer": "Réponse à la question 1."},
                {"question": "Question 2 ?", "answer": "Réponse à la question 2."},
            ],
            "style": "cards"  # cards, simple, numbered
        }
    
    def to_html(self, context=None):
        c = self.content
        title = c.get('title', '')
        items = c.get('items', [])
        style = c.get('style', 'cards')
        
        title_html = f'<h3 style="margin:0 0 20px;color:{KRYSTO_DARK};text-align:center;">{title}</h3>' if title else ""
        
        items_html = ""
        for i, item in enumerate(items):
            q = item.get('question', '')
            a = item.get('answer', '')
            
            if style == "cards":
                items_html += f'''<div style="background:#f8f9fa;padding:15px 20px;border-radius:10px;margin-bottom:10px;border-left:4px solid {KRYSTO_PRIMARY};">
                    <p style="margin:0 0 8px;font-weight:bold;color:{KRYSTO_DARK};">❓ {q}</p>
                    <p style="margin:0;color:#666;font-size:14px;">{a}</p>
                </div>'''
            elif style == "numbered":
                items_html += f'''<div style="padding:15px 0;border-bottom:1px solid #eee;">
                    <p style="margin:0 0 8px;font-weight:bold;color:{KRYSTO_PRIMARY};">{i+1}. {q}</p>
                    <p style="margin:0;color:#666;font-size:14px;padding-left:20px;">{a}</p>
                </div>'''
            else:
                items_html += f'''<div style="padding:12px 0;">
                    <p style="margin:0 0 5px;font-weight:bold;color:{KRYSTO_DARK};">{q}</p>
                    <p style="margin:0;color:#666;font-size:14px;">{a}</p>
                </div>'''
        
        return f'<div style="padding:10px 0;">{title_html}{items_html}</div>'
    
    def get_preview_text(self):
        return f"❓ FAQ ({len(self.content.get('items', []))} questions)"


class ComparisonBlock(EmailBlock):
    """Tableau de comparaison"""
    BLOCK_TYPE = "comparison"
    BLOCK_ICON = "⚖️"
    BLOCK_NAME = "Comparaison"
    
    @classmethod
    def get_default_content(cls):
        return {
            "title": "",
            "option_1": {"name": "Option A", "features": ["Feature 1", "Feature 2"], "price": "", "highlight": False},
            "option_2": {"name": "Option B", "features": ["Feature 1", "Feature 2", "Feature 3"], "price": "", "highlight": True},
            "style": "cards"
        }
    
    def to_html(self, context=None):
        c = self.content
        title = c.get('title', '')
        opt1 = c.get('option_1', {})
        opt2 = c.get('option_2', {})
        
        title_html = f'<h3 style="margin:0 0 20px;text-align:center;color:{KRYSTO_DARK};">{title}</h3>' if title else ""
        
        def render_option(opt, highlight=False):
            name = opt.get('name', '')
            features = opt.get('features', [])
            price = opt.get('price', '')
            
            bg = f"linear-gradient(135deg, {KRYSTO_PRIMARY}10, {KRYSTO_SECONDARY}10)" if highlight else "#f8f9fa"
            border = f"2px solid {KRYSTO_PRIMARY}" if highlight else "1px solid #e0e0e0"
            badge = f'<span style="background:{KRYSTO_SECONDARY};color:{KRYSTO_DARK};padding:3px 10px;border-radius:10px;font-size:10px;position:absolute;top:-10px;right:10px;">RECOMMANDÉ</span>' if highlight else ""
            
            features_html = "".join(f'<div style="padding:8px 0;border-bottom:1px solid #eee;"><span style="color:{KRYSTO_SECONDARY};margin-right:8px;">✓</span>{f}</div>' for f in features)
            price_html = f'<div style="font-size:24px;font-weight:bold;color:{KRYSTO_PRIMARY};margin-top:15px;">{price}</div>' if price else ""
            
            return f'''<div style="flex:1;background:{bg};border:{border};border-radius:12px;padding:20px;margin:5px;position:relative;text-align:center;">
                {badge}
                <h4 style="margin:0 0 15px;color:{KRYSTO_DARK};">{name}</h4>
                <div style="text-align:left;">{features_html}</div>
                {price_html}
            </div>'''
        
        return f'''<div style="padding:10px 0;">
            {title_html}
            <div style="display:flex;gap:10px;">
                {render_option(opt1, opt1.get('highlight', False))}
                {render_option(opt2, opt2.get('highlight', False))}
            </div>
        </div>'''
    
    def get_preview_text(self):
        opt1 = self.content.get('option_1', {}).get('name', 'A')
        opt2 = self.content.get('option_2', {}).get('name', 'B')
        return f"⚖️ {opt1} vs {opt2}"


class CouponBlock(EmailBlock):
    """Coupon style ticket à découper"""
    BLOCK_TYPE = "coupon"
    BLOCK_ICON = "🎟️"
    BLOCK_NAME = "Coupon"
    
    @classmethod
    def get_default_content(cls):
        return {
            "title": "BON DE RÉDUCTION",
            "value": "-20%",
            "description": "Sur votre prochain achat",
            "code": "PROMO20",
            "expiry": "Valable jusqu'au 31/12/2025",
            "style": "ticket"  # ticket, simple, premium
        }
    
    def to_html(self, context=None):
        c = self.content
        title = c.get('title', 'BON DE RÉDUCTION')
        value = c.get('value', '-20%')
        description = c.get('description', '')
        code = c.get('code', '')
        expiry = c.get('expiry', '')
        style = c.get('style', 'ticket')
        
        if style == "ticket":
            return f'''<div style="background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});border-radius:15px;padding:3px;margin:20px 0;">
                <div style="background:#fff;border-radius:12px;padding:25px;text-align:center;border:2px dashed {KRYSTO_PRIMARY};">
                    <p style="margin:0;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:2px;">{title}</p>
                    <p style="margin:10px 0;font-size:48px;font-weight:bold;color:{KRYSTO_PRIMARY};">{value}</p>
                    <p style="margin:0 0 15px;color:#666;">{description}</p>
                    <div style="background:#f5f5f5;padding:12px 25px;border-radius:8px;display:inline-block;">
                        <span style="font-family:monospace;font-size:18px;font-weight:bold;letter-spacing:3px;">{code}</span>
                    </div>
                    <p style="margin:15px 0 0;font-size:11px;color:#999;">{expiry}</p>
                </div>
            </div>'''
        elif style == "premium":
            return f'''<div style="background:linear-gradient(135deg,#1a1a1a,#333);border-radius:15px;padding:30px;text-align:center;margin:20px 0;">
                <p style="margin:0;font-size:11px;color:gold;text-transform:uppercase;letter-spacing:3px;">{title}</p>
                <p style="margin:15px 0;font-size:52px;font-weight:bold;background:linear-gradient(135deg,gold,#f5d742);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{value}</p>
                <p style="margin:0 0 20px;color:#ccc;">{description}</p>
                <div style="background:rgba(255,215,0,0.2);border:1px solid gold;padding:12px 30px;border-radius:8px;display:inline-block;">
                    <span style="font-family:monospace;font-size:18px;font-weight:bold;color:gold;letter-spacing:3px;">{code}</span>
                </div>
                <p style="margin:20px 0 0;font-size:11px;color:#888;">{expiry}</p>
            </div>'''
        else:
            return f'''<div style="border:2px solid {KRYSTO_PRIMARY};border-radius:10px;padding:20px;text-align:center;margin:20px 0;">
                <p style="margin:0;font-size:11px;color:#888;">{title}</p>
                <p style="margin:10px 0;font-size:36px;font-weight:bold;color:{KRYSTO_PRIMARY};">{value}</p>
                <p style="margin:0 0 10px;color:#666;">{description}</p>
                <code style="background:#f5f5f5;padding:8px 20px;font-size:16px;">{code}</code>
                <p style="margin:10px 0 0;font-size:11px;color:#999;">{expiry}</p>
            </div>'''
    
    def get_preview_text(self):
        return f"🎟️ {self.content.get('value', '-20%')}"


class StepsBlock(EmailBlock):
    """Étapes numérotées avec icônes"""
    BLOCK_TYPE = "steps"
    BLOCK_ICON = "1️⃣"
    BLOCK_NAME = "Étapes"
    
    @classmethod
    def get_default_content(cls):
        return {
            "title": "",
            "steps": [
                {"title": "Étape 1", "description": "Description de l'étape 1"},
                {"title": "Étape 2", "description": "Description de l'étape 2"},
                {"title": "Étape 3", "description": "Description de l'étape 3"},
            ],
            "style": "numbered"  # numbered, icons, circles
        }
    
    def to_html(self, context=None):
        c = self.content
        title = c.get('title', '')
        steps = c.get('steps', [])
        style = c.get('style', 'numbered')
        
        title_html = f'<h3 style="margin:0 0 25px;text-align:center;color:{KRYSTO_DARK};">{title}</h3>' if title else ""
        
        steps_html = ""
        for i, step in enumerate(steps):
            step_title = step.get('title', '')
            step_desc = step.get('description', '')
            is_last = i == len(steps) - 1
            
            if style == "circles":
                steps_html += f'''<div style="display:flex;margin-bottom:{0 if is_last else 20}px;">
                    <div style="width:50px;height:50px;background:{KRYSTO_PRIMARY};color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:18px;flex-shrink:0;">{i+1}</div>
                    <div style="margin-left:20px;padding-top:5px;">
                        <h4 style="margin:0 0 5px;color:{KRYSTO_DARK};">{step_title}</h4>
                        <p style="margin:0;color:#666;font-size:14px;">{step_desc}</p>
                    </div>
                </div>'''
            elif style == "icons":
                icons = ["🎯", "⚡", "🚀", "🎉", "✨"]
                icon = icons[i % len(icons)]
                steps_html += f'''<div style="text-align:center;display:inline-block;width:30%;vertical-align:top;padding:15px;">
                    <div style="font-size:36px;margin-bottom:10px;">{icon}</div>
                    <h4 style="margin:0 0 8px;color:{KRYSTO_DARK};">{step_title}</h4>
                    <p style="margin:0;color:#666;font-size:13px;">{step_desc}</p>
                </div>'''
            else:
                line = f'<div style="position:absolute;left:24px;top:50px;bottom:0;width:2px;background:#e0e0e0;"></div>' if not is_last else ''
                steps_html += f'''<div style="position:relative;padding-left:65px;padding-bottom:{25 if not is_last else 0}px;">
                    <div style="position:absolute;left:0;top:0;width:50px;height:50px;background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:20px;">{i+1}</div>
                    {line}
                    <h4 style="margin:0 0 5px;color:{KRYSTO_DARK};padding-top:5px;">{step_title}</h4>
                    <p style="margin:0;color:#666;font-size:14px;">{step_desc}</p>
                </div>'''
        
        wrapper_style = 'text-align:center;' if style == "icons" else ''
        return f'<div style="padding:15px 0;{wrapper_style}">{title_html}{steps_html}</div>'
    
    def get_preview_text(self):
        return f"1️⃣ {len(self.content.get('steps', []))} étapes"


class HighlightBoxBlock(EmailBlock):
    """Box mise en avant stylisée"""
    BLOCK_TYPE = "highlight_box"
    BLOCK_ICON = "🔥"
    BLOCK_NAME = "Box vedette"
    
    @classmethod
    def get_default_content(cls):
        return {
            "title": "Important !",
            "text": "Contenu mis en avant...",
            "style": "gradient",  # gradient, neon, minimal, bordered
            "icon": "🔥"
        }
    
    def to_html(self, context=None):
        c = self.content
        title = c.get('title', '')
        text = c.get('text', '')
        style = c.get('style', 'gradient')
        icon = c.get('icon', '🔥')
        
        if style == "gradient":
            return f'''<div style="background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});border-radius:15px;padding:25px;text-align:center;margin:15px 0;">
                <span style="font-size:36px;">{icon}</span>
                <h3 style="margin:15px 0 10px;color:white;">{title}</h3>
                <p style="margin:0;color:rgba(255,255,255,0.9);font-size:15px;">{text}</p>
            </div>'''
        elif style == "neon":
            return f'''<div style="background:#1a1a1a;border:2px solid {KRYSTO_SECONDARY};border-radius:15px;padding:25px;text-align:center;margin:15px 0;box-shadow:0 0 20px {KRYSTO_SECONDARY}40;">
                <span style="font-size:36px;">{icon}</span>
                <h3 style="margin:15px 0 10px;color:{KRYSTO_SECONDARY};">{title}</h3>
                <p style="margin:0;color:#ccc;font-size:15px;">{text}</p>
            </div>'''
        elif style == "bordered":
            return f'''<div style="border:3px solid {KRYSTO_PRIMARY};border-radius:15px;padding:25px;text-align:center;margin:15px 0;">
                <span style="font-size:36px;">{icon}</span>
                <h3 style="margin:15px 0 10px;color:{KRYSTO_PRIMARY};">{title}</h3>
                <p style="margin:0;color:#666;font-size:15px;">{text}</p>
            </div>'''
        else:
            return f'''<div style="background:#f8f9fa;border-radius:15px;padding:25px;text-align:center;margin:15px 0;">
                <span style="font-size:36px;">{icon}</span>
                <h3 style="margin:15px 0 10px;color:{KRYSTO_DARK};">{title}</h3>
                <p style="margin:0;color:#666;font-size:15px;">{text}</p>
            </div>'''
    
    def get_preview_text(self):
        return f"🔥 {self.content.get('title', 'Box vedette')}"


# Templates prédéfinis pour l'éditeur
EMAIL_TEMPLATES = {
    "blank": {
        "name": "Vide",
        "description": "Template vide",
        "blocks": []
    },
    "newsletter": {
        "name": "📰 Newsletter",
        "description": "Newsletter classique avec article",
        "blocks": [
            {"type": "hero", "content": {"image_url": "", "title": "Notre Newsletter", "subtitle": "Les dernières actualités", "height": 300}},
            {"type": "text", "content": {"text": "Bonjour {{name}},\n\nVoici les dernières nouvelles de notre équipe...", "font_size": 15}},
            {"type": "divider", "content": {}},
            {"type": "title", "content": {"text": "À la une", "level": "h2"}},
            {"type": "text", "content": {"text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."}},
            {"type": "button", "content": {"text": "Lire la suite", "url": ""}},
            {"type": "spacer", "content": {"height": 30}},
            {"type": "social", "content": {}},
            {"type": "unsubscribe", "content": {}},
        ]
    },
    "promo": {
        "name": "🎉 Promotion",
        "description": "Email promotionnel avec offre",
        "blocks": [
            {"type": "banner", "content": {"text": "🎉 OFFRE EXCEPTIONNELLE", "subtext": "Valable jusqu'au {{date}}", "style": "gradient", "size": "large"}},
            {"type": "spacer", "content": {"height": 20}},
            {"type": "gradient_text", "content": {"text": "-30%", "font_size": 72}},
            {"type": "text", "content": {"text": "Sur une sélection de produits !", "align": "center", "font_size": 18}},
            {"type": "spacer", "content": {"height": 20}},
            {"type": "promo_code", "content": {"code": "PROMO30", "description": "Utilisez ce code à la caisse"}},
            {"type": "countdown", "content": {"title": "Fin de l'offre dans", "days": 3, "hours": 12, "minutes": 30}},
            {"type": "button", "content": {"text": "🛒 J'en profite !", "style": "gradient", "full_width": True}},
            {"type": "spacer", "content": {"height": 30}},
            {"type": "icon_row", "content": {}},
            {"type": "unsubscribe", "content": {}},
        ]
    },
    "welcome": {
        "name": "👋 Bienvenue",
        "description": "Email de bienvenue nouveau client",
        "blocks": [
            {"type": "hero", "content": {"title": "Bienvenue {{name}} !", "subtitle": "Nous sommes ravis de vous compter parmi nous", "height": 280}},
            {"type": "text", "content": {"text": "Merci de votre confiance ! Voici ce que vous pouvez faire maintenant :"}},
            {"type": "timeline", "content": {"items": [
                {"icon": "1", "title": "Découvrez nos produits", "description": "Parcourez notre catalogue"},
                {"icon": "2", "title": "Créez votre profil", "description": "Personnalisez votre expérience"},
                {"icon": "3", "title": "Profitez d'avantages", "description": "Offres exclusives membres"}
            ]}},
            {"type": "callout", "content": {"title": "🎁 Cadeau de bienvenue", "text": "Utilisez le code BIENVENUE pour -10% sur votre première commande !", "style": "success"}},
            {"type": "button", "content": {"text": "Commencer", "style": "gradient"}},
            {"type": "spacer", "content": {"height": 20}},
            {"type": "contact", "content": {}},
            {"type": "signature", "content": {}},
        ]
    },
    "product": {
        "name": "🛍️ Produit",
        "description": "Présentation de produit",
        "blocks": [
            {"type": "title", "content": {"text": "Découvrez notre nouveauté", "align": "center"}},
            {"type": "product", "content": {"name": "Nom du produit", "price": "9 900 XPF", "description": "Description du produit..."}},
            {"type": "feature_box", "content": {}},
            {"type": "testimonial", "content": {}},
            {"type": "rating", "content": {"rating": 5, "text": "Noté 5/5 par nos clients"}},
            {"type": "button", "content": {"text": "Commander maintenant", "style": "gradient", "full_width": True}},
            {"type": "icon_row", "content": {}},
        ]
    },
    "event": {
        "name": "📅 Événement",
        "description": "Invitation à un événement",
        "blocks": [
            {"type": "hero", "content": {"title": "Vous êtes invité !", "subtitle": "Un événement exceptionnel"}},
            {"type": "title", "content": {"text": "📅 Nom de l'événement", "align": "center"}},
            {"type": "stats", "content": {"stats": [
                {"value": "15", "label": "Janvier 2025"},
                {"value": "18h", "label": "Heure"},
                {"value": "100", "label": "Places"}
            ]}},
            {"type": "text", "content": {"text": "Description de l'événement et des activités prévues..."}},
            {"type": "map", "content": {}},
            {"type": "button", "content": {"text": "Je m'inscris", "style": "gradient"}},
            {"type": "countdown", "content": {"title": "J-"}},
            {"type": "contact", "content": {}},
        ]
    },
    "invoice_reminder": {
        "name": "💰 Rappel facture",
        "description": "Rappel de paiement",
        "blocks": [
            {"type": "alert", "content": {"text": "Rappel de paiement", "type": "warning", "style": "banner"}},
            {"type": "text", "content": {"text": "Bonjour {{name}},\n\nNous vous rappelons que vous avez un solde en cours :"}},
            {"type": "table", "content": {"headers": ["Période", "Montant"], "rows": [["M1 (0-30j)", "{{dette_m1}}"], ["M2 (30-60j)", "{{dette_m2}}"], ["M3 (60-90j)", "{{dette_m3}}"], ["Total", "{{dette_total}}"]]}},
            {"type": "callout", "content": {"title": "💳 Comment payer ?", "text": "Virement bancaire, chèque ou espèces à notre boutique.", "style": "info"}},
            {"type": "button", "content": {"text": "Nous contacter", "url": "mailto:" + COMPANY_EMAIL}},
            {"type": "signature", "content": {}},
        ]
    },
    "thank_you": {
        "name": "🙏 Remerciement",
        "description": "Email de remerciement après achat",
        "blocks": [
            {"type": "gradient_text", "content": {"text": "Merci !", "font_size": 48}},
            {"type": "text", "content": {"text": "Bonjour {{name}},\n\nNous tenons à vous remercier pour votre confiance et votre récent achat.", "align": "center"}},
            {"type": "callout", "content": {"title": "Votre avis compte !", "text": "N'hésitez pas à nous laisser un avis sur notre page ou à nous contacter si vous avez des questions.", "style": "success"}},
            {"type": "rating", "content": {"style": "stars", "text": "Évaluez votre expérience"}},
            {"type": "divider_icon", "content": {"icon": "♥️"}},
            {"type": "text", "content": {"text": "À très bientôt !", "align": "center"}},
            {"type": "signature", "content": {}},
        ]
    },
    "eco_tips": {
        "name": "🌱 Éco-conseils",
        "description": "Newsletter écologique avec conseils",
        "blocks": [
            {"type": "hero", "content": {"title": "♻️ Éco-conseils du mois", "subtitle": "Adoptons les bons gestes ensemble"}},
            {"type": "text", "content": {"text": "Bonjour {{name}},\n\nDécouvrez nos conseils pour un mode de vie plus durable :"}},
            {"type": "checklist", "content": {"title": "Les gestes simples", "items": [
                {"text": "Trier ses déchets plastiques", "checked": True},
                {"text": "Utiliser des contenants réutilisables", "checked": True},
                {"text": "Privilégier les produits recyclés", "checked": False}
            ]}},
            {"type": "before_after", "content": {"before_label": "Jetable", "after_label": "Recyclé"}},
            {"type": "number_highlight", "content": {"number": "8M", "suffix": "", "label": "tonnes de plastique dans les océans chaque année"}},
            {"type": "button", "content": {"text": "Découvrir nos produits recyclés", "style": "gradient"}},
            {"type": "social", "content": {}},
        ]
    },
    "new_arrival": {
        "name": "✨ Nouveau produit",
        "description": "Annonce de nouvelle collection/produit",
        "blocks": [
            {"type": "banner", "content": {"text": "✨ NOUVEAUTÉ", "subtext": "Découvrez en exclusivité", "style": "gradient", "size": "large"}},
            {"type": "spacer", "content": {"height": 20}},
            {"type": "image", "content": {"align": "center", "border_radius": 15}},
            {"type": "gradient_text", "content": {"text": "Nom du produit", "font_size": 32}},
            {"type": "text", "content": {"text": "Description du nouveau produit et ses caractéristiques exceptionnelles...", "align": "center"}},
            {"type": "feature_box", "content": {"features": [
                {"icon": "♻️", "title": "100% Recyclé", "description": "Fabriqué à partir de plastique recyclé"},
                {"icon": "🇳🇨", "title": "Made in NC", "description": "Conçu et fabriqué localement"},
                {"icon": "💪", "title": "Durable", "description": "Résistant et longue durée"}
            ]}},
            {"type": "countdown", "content": {"title": "Disponible dans"}},
            {"type": "button", "content": {"text": "Je veux être informé(e)", "style": "gradient", "full_width": True}},
        ]
    },
    "survey": {
        "name": "📊 Sondage",
        "description": "Email avec sondage/questionnaire",
        "blocks": [
            {"type": "title", "content": {"text": "📊 Votre avis nous intéresse !", "align": "center"}},
            {"type": "text", "content": {"text": "Bonjour {{name}},\n\nAidez-nous à améliorer nos services en répondant à quelques questions :"}},
            {"type": "callout", "content": {"title": "⏱️ 2 minutes seulement", "text": "Ce questionnaire rapide nous permettra de mieux vous servir.", "style": "info"}},
            {"type": "avatar_group", "content": {"text": "Rejoignez nos clients satisfaits"}},
            {"type": "button", "content": {"text": "Répondre au sondage", "style": "gradient", "full_width": True}},
            {"type": "divider", "content": {}},
            {"type": "text", "content": {"text": "En remerciement, recevez un code promo exclusif !", "align": "center", "font_size": 13}},
        ]
    },
    "seasonal": {
        "name": "🎄 Saisonnier",
        "description": "Template pour fêtes/saisons",
        "blocks": [
            {"type": "hero", "content": {"title": "🎄 Joyeuses Fêtes", "subtitle": "De la part de toute l'équipe", "height": 250}},
            {"type": "text", "content": {"text": "Cher(e) {{name}},\n\nToute l'équipe vous souhaite de merveilleuses fêtes de fin d'année !", "align": "center"}},
            {"type": "stats", "content": {"stats": [
                {"value": "🎁", "label": "Offres spéciales"},
                {"value": "🎄", "label": "Horaires fêtes"},
                {"value": "📦", "label": "Livraison express"}
            ]}},
            {"type": "promo_code", "content": {"code": "FETES2025", "description": "-15% sur tout le site"}},
            {"type": "callout", "content": {"title": "📅 Horaires exceptionnels", "text": "Fermé du 24 au 26 décembre. Réouverture le 27.", "style": "warning"}},
            {"type": "button", "content": {"text": "Voir les offres", "style": "gradient"}},
            {"type": "signature", "content": {}},
        ]
    },
    "abandoned_cart": {
        "name": "🛒 Panier abandonné",
        "description": "Relance panier non finalisé",
        "blocks": [
            {"type": "title", "content": {"text": "🛒 Vous avez oublié quelque chose ?", "align": "center"}},
            {"type": "text", "content": {"text": "Bonjour {{name}},\n\nVotre panier vous attend ! Finalisez votre commande avant qu'il ne soit trop tard."}},
            {"type": "alert", "content": {"text": "Stock limité - Ne tardez pas !", "type": "warning", "style": "banner"}},
            {"type": "product", "content": {"name": "Produit dans votre panier", "price": "5 900 XPF"}},
            {"type": "icon_row", "content": {"items": [
                {"icon": "🚚", "text": "Livraison gratuite"},
                {"icon": "🔒", "text": "Paiement sécurisé"},
                {"icon": "↩️", "text": "Retour gratuit"}
            ]}},
            {"type": "button", "content": {"text": "Finaliser ma commande", "style": "gradient", "full_width": True}},
            {"type": "callout", "content": {"title": "🎁 Code exclusif", "text": "Utilisez RETOUR10 pour -10% sur votre commande", "style": "success"}},
        ]
    },
    "order_confirmation": {
        "name": "✅ Confirmation commande",
        "description": "Confirmation de commande client",
        "blocks": [
            {"type": "alert", "content": {"text": "✅ Commande confirmée !", "type": "success", "style": "banner"}},
            {"type": "text", "content": {"text": "Bonjour {{name}},\n\nMerci pour votre commande ! Voici le récapitulatif :"}},
            {"type": "table", "content": {"headers": ["Produit", "Qté", "Prix"], "rows": [
                ["Produit exemple", "1", "5 900 XPF"],
                ["", "Total", "5 900 XPF"]
            ], "style": "bordered"}},
            {"type": "timeline", "content": {"items": [
                {"icon": "✓", "title": "Commande reçue", "description": "Votre commande est enregistrée"},
                {"icon": "📦", "title": "Préparation", "description": "Sous 24-48h"},
                {"icon": "🚚", "title": "Livraison", "description": "Sous 3-5 jours"}
            ]}},
            {"type": "contact", "content": {"style": "inline"}},
            {"type": "signature", "content": {}},
        ]
    },
    "referral": {
        "name": "👫 Parrainage",
        "description": "Programme de parrainage",
        "blocks": [
            {"type": "gradient_text", "content": {"text": "Parrainez vos amis !", "font_size": 36}},
            {"type": "text", "content": {"text": "Bonjour {{name}},\n\nFaites découvrir nos produits à vos proches et gagnez des récompenses !", "align": "center"}},
            {"type": "stats", "content": {"stats": [
                {"value": "1000", "label": "XPF pour vous"},
                {"value": "1000", "label": "XPF pour eux"},
                {"value": "∞", "label": "Parrainages"}
            ]}},
            {"type": "timeline", "content": {"items": [
                {"icon": "1️⃣", "title": "Partagez", "description": "Envoyez votre code à vos amis"},
                {"icon": "2️⃣", "title": "Ils commandent", "description": "Avec -10% de réduction"},
                {"icon": "3️⃣", "title": "Vous gagnez", "description": "1000 XPF de crédit"}
            ]}},
            {"type": "promo_code", "content": {"code": "PARRAIN-{{code_parrainage}}", "description": "Votre code de parrainage unique"}},
            {"type": "callout", "content": {"title": "📱 Partagez facilement", "text": "Envoyez ce code par SMS, email ou réseaux sociaux à vos amis !", "style": "info"}},
            {"type": "button", "content": {"text": "Partager maintenant", "style": "gradient", "full_width": True}},
        ]
    },
}


BLOCK_TYPES = {
    "text": TextBlock, "title": TitleBlock, "image": ImageBlock, "button": ButtonBlock,
    "divider": DividerBlock, "spacer": SpacerBlock, "quote": QuoteBlock,
    "list": ListBlock, "promo_code": PromoCodeBlock, "social": SocialBlock, "html": HtmlBlock,
    # Blocs avancés layout
    "image_grid": ImageGridBlock, "columns": ColumnsBlock, "hero": HeroBlock,
    "card": CardBlock, "product": ProductBlock, "testimonial": TestimonialBlock,
    "video": VideoBlock, "countdown": CountdownBlock, "gallery": GalleryBlock,
    "accordion": AccordionBlock, "stats": StatsBlock, "map": MapBlock,
    "footer_links": FooterLinksBlock,
    # Blocs pro
    "unsubscribe": UnsubscribeBlock, "signature": SignatureBlock, "alert": AlertBlock,
    "pricing": PricingBlock, "timeline": TimelineBlock, "team": TeamBlock,
    "rating": RatingBlock, "feature_box": FeatureBoxBlock, "table": TableBlock,
    "progress": ProgressBlock, "separator_text": SeparatorTextBlock,
    # Blocs créatifs
    "before_after": BeforeAfterBlock, "icon_row": IconRowBlock, "callout": CalloutBlock,
    "checklist": ChecklistBlock, "contact": ContactBlock, "banner": BannerBlock,
    "avatar_group": AvatarGroupBlock, "gradient_text": GradientTextBlock,
    "logo_cloud": LogoCloudBlock, "number_highlight": NumberHighlightBlock,
    "divider_icon": DividerIconBlock,
    # Nouveaux blocs avancés
    "qr_code": QRCodeBlock, "faq": FaqBlock, "comparison": ComparisonBlock,
    "coupon": CouponBlock, "steps": StepsBlock, "highlight_box": HighlightBoxBlock,
}

# Catégories de blocs pour l'UI - Total: 52 blocs
BLOCK_CATEGORIES = {
    "📝 Contenu": ["text", "title", "quote", "list", "accordion", "table", "checklist", "faq"],
    "🖼️ Médias": ["image", "image_grid", "gallery", "video", "before_after", "logo_cloud"],
    "📐 Layout": ["columns", "hero", "card", "spacer", "divider", "separator_text", "divider_icon"],
    "🎯 Actions": ["button", "promo_code", "countdown", "alert", "banner", "callout", "highlight_box"],
    "🛍️ Commerce": ["product", "pricing", "testimonial", "rating", "stats", "progress", "number_highlight", "coupon", "comparison"],
    "👥 Équipe": ["team", "signature", "timeline", "feature_box", "avatar_group", "contact", "steps"],
    "🎨 Design": ["gradient_text", "icon_row", "qr_code"],
    "📍 Footer": ["social", "footer_links", "map", "unsubscribe"],
    "🔧 Avancé": ["html"],
}


# ============================================================================
# EMAIL DESIGNER
# ============================================================================
class EmailDesigner:
    def __init__(self):
        self.blocks = []
        self.settings = {
            "header_style": "gradient", "header_logo": "", "header_title": COMPANY_NAME,
            "header_subtitle": "", "footer_text": f"© {datetime.now().year} {COMPANY_NAME}",
            "footer_address": COMPANY_ADDRESS, "footer_unsubscribe": True,
            "content_width": 600, "bg_color": "#f4f4f4", "content_bg": "#ffffff",
            "font_family": "Segoe UI, Tahoma, Geneva, Verdana, sans-serif", "preheader": ""}
    
    def add_block(self, block): self.blocks.append(block); return len(self.blocks) - 1
    def insert_block(self, index, block): self.blocks.insert(index, block)
    def remove_block(self, index):
        if 0 <= index < len(self.blocks): return self.blocks.pop(index)
    def move_block(self, from_idx, to_idx):
        if 0 <= from_idx < len(self.blocks) and 0 <= to_idx < len(self.blocks):
            self.blocks.insert(to_idx, self.blocks.pop(from_idx)); return True
        return False
    def duplicate_block(self, index):
        if 0 <= index < len(self.blocks):
            self.blocks.insert(index + 1, self.blocks[index].clone()); return index + 1
        return -1
    def clear_blocks(self): self.blocks = []
    def to_dict(self):
        return {"settings": self.settings, "blocks": [{"type": b.BLOCK_TYPE, "content": b.content} for b in self.blocks]}
    def from_dict(self, data):
        self.settings = {**self.settings, **data.get("settings", {})}
        self.blocks = []
        for bd in data.get("blocks", []):
            if bd["type"] in BLOCK_TYPES: self.blocks.append(BLOCK_TYPES[bd["type"]](bd["content"]))
    
    def generate_header(self):
        s = self.settings
        if s['header_style'] == "none": return ""
        logo = f'<img src="{s["header_logo"]}" alt="{s["header_title"]}" style="max-height:60px;margin-bottom:15px;">' if s['header_logo'] else ""
        subtitle = f'<p style="margin:10px 0 0 0;font-size:14px;color:rgba(255,255,255,0.9);">{s["header_subtitle"]}</p>' if s['header_subtitle'] else ""
        if s['header_style'] == "gradient":
            return f'<div style="background:linear-gradient(135deg,{KRYSTO_PRIMARY} 0%,{KRYSTO_SECONDARY} 100%);padding:40px 30px;text-align:center;">{logo}<h1 style="margin:0;color:white;font-size:28px;font-weight:bold;">{s["header_title"]}</h1>{subtitle}</div>'
        elif s['header_style'] == "simple":
            return f'<div style="background-color:{KRYSTO_PRIMARY};padding:30px;text-align:center;">{logo}<h1 style="margin:0;color:white;font-size:24px;">{s["header_title"]}</h1>{subtitle}</div>'
        return f'<div style="padding:25px;text-align:center;border-bottom:3px solid {KRYSTO_SECONDARY};">{logo}<h1 style="margin:0;color:{KRYSTO_PRIMARY};font-size:24px;">{s["header_title"]}</h1></div>'
    
    def generate_footer(self):
        s = self.settings
        unsub = '<p style="margin:15px 0 0 0;"><a href="{{unsubscribe_url}}" style="color:#999;font-size:11px;">Se désinscrire</a></p>' if s['footer_unsubscribe'] else ""
        
        # Infos entreprise
        ridet_html = f'<span style="margin:0 10px;">RIDET: {COMPANY_RIDET}</span>' if COMPANY_RIDET else ""
        phone_html = f'<span style="margin:0 10px;">📞 {COMPANY_PHONE}</span>' if COMPANY_PHONE else ""
        
        extra_info = ""
        if ridet_html or phone_html:
            extra_info = f'<p style="margin:8px 0 0 0;color:rgba(255,255,255,0.5);font-size:11px;">{phone_html}{ridet_html}</p>'
        
        return f'''<div style="background-color:{KRYSTO_DARK};padding:30px;text-align:center;">
            <p style="margin:0;color:rgba(255,255,255,0.7);font-size:13px;">{s["footer_text"]}</p>
            <p style="margin:10px 0 0 0;color:rgba(255,255,255,0.5);font-size:12px;">{s["footer_address"]}</p>
            {extra_info}{unsub}
        </div>'''
    
    def generate_html(self, context=None):
        s = self.settings
        preheader = f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">{s["preheader"]}&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;</div>' if s['preheader'] else ""
        blocks_html = "".join(b.to_html(context) for b in self.blocks)
        
        # Structure HTML optimisée pour éviter les spams
        return f'''<!DOCTYPE html>
<html lang="fr" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no">
    <title>{s['header_title']}</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style>
        body{{margin:0;padding:0;font-family:{s['font_family']};background-color:{s['bg_color']};-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}}
        table{{border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;}}
        img{{border:0;height:auto;line-height:100%;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;max-width:100%;}}
        a{{color:{KRYSTO_PRIMARY};text-decoration:none;}}
        *{{box-sizing:border-box;}}
        @media only screen and (max-width:600px){{
            .email-container{{width:100%!important;}}
            .content-padding{{padding:20px!important;}}
            .stack-column{{display:block!important;width:100%!important;}}
        }}
    </style>
</head>
<body style="margin:0;padding:0;background-color:{s['bg_color']};word-spacing:normal;">
    {preheader}
    <div role="article" aria-roledescription="email" lang="fr" style="text-size-adjust:100%;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:{s['bg_color']};">
            <tr>
                <td align="center" style="padding:20px 10px;">
                    <div class="email-container" style="max-width:{s['content_width']}px;width:100%;margin:0 auto;background-color:{s['content_bg']};border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
                        {self.generate_header()}
                        <div class="content-padding" style="padding:30px;">
                            {blocks_html}
                        </div>
                        {self.generate_footer()}
                    </div>
                </td>
            </tr>
        </table>
    </div>
</body>
</html>'''
    
    def preview_in_browser(self):
        html = self.generate_html()
        with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            webbrowser.open('file://' + f.name)


# ============================================================================
# BASE DE DONNÉES
# ============================================================================
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    
    # Table clients avec suivi impayés
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
        client_type TEXT DEFAULT 'particulier',
        newsletter INTEGER DEFAULT 1,
        notes TEXT,
        -- Infos Pro (NC)
        ridet TEXT,
        forme_juridique TEXT,
        nom_gerant TEXT,
        -- Blocage client
        bloque INTEGER DEFAULT 0,
        motif_blocage TEXT,
        date_blocage TEXT,
        -- Suivi impayés pour les pros
        dette_m1 REAL DEFAULT 0,
        dette_m2 REAL DEFAULT 0,
        dette_m3 REAL DEFAULT 0,
        dette_m3plus REAL DEFAULT 0,
        date_dette_m1 TEXT,
        date_dette_m2 TEXT,
        date_dette_m3 TEXT,
        dernier_rappel TEXT,
        date_created TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table produits
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        price REAL DEFAULT 0,
        cost REAL DEFAULT 0,
        stock INTEGER DEFAULT 0,
        image_url TEXT,
        image_url_2 TEXT,
        image_url_3 TEXT,
        active INTEGER DEFAULT 1,
        date_created TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table paramètres (catalogue, etc.)
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # Table dépôts-ventes (liés aux clients pro)
    c.execute('''CREATE TABLE IF NOT EXISTS depots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        commission_percent REAL DEFAULT 0,
        notes TEXT,
        active INTEGER DEFAULT 1,
        date_created TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )''')
    
    # Table des produits en dépôt-vente
    c.execute('''CREATE TABLE IF NOT EXISTS depot_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        depot_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity_deposited INTEGER DEFAULT 0,
        quantity_sold INTEGER DEFAULT 0,
        quantity_returned INTEGER DEFAULT 0,
        quantity_invoiced INTEGER DEFAULT 0,
        price_depot REAL,
        discount_percent REAL DEFAULT 0,
        date_deposit TEXT DEFAULT CURRENT_TIMESTAMP,
        last_update TEXT,
        notes TEXT,
        FOREIGN KEY (depot_id) REFERENCES depots(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    
    # Table historique dépôt-vente
    c.execute('''CREATE TABLE IF NOT EXISTS depot_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        depot_id INTEGER NOT NULL,
        product_id INTEGER,
        action TEXT,
        quantity INTEGER,
        amount REAL,
        date_action TEXT DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (depot_id) REFERENCES depots(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    
    # Table templates email
    c.execute('''CREATE TABLE IF NOT EXISTS email_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        subject TEXT,
        template_type TEXT DEFAULT 'marketing',
        design_json TEXT,
        date_created TEXT DEFAULT CURRENT_TIMESTAMP,
        date_modified TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table campagnes email
    c.execute('''CREATE TABLE IF NOT EXISTS email_campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        subject TEXT,
        template_id INTEGER,
        recipients_count INTEGER DEFAULT 0,
        sent_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'brouillon',
        date_created TEXT DEFAULT CURRENT_TIMESTAMP,
        date_sent TEXT,
        FOREIGN KEY (template_id) REFERENCES email_templates(id)
    )''')
    
    # Table groupes de clients
    c.execute('''CREATE TABLE IF NOT EXISTS client_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        color TEXT DEFAULT '#6d74ab',
        date_created TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table membres des groupes
    c.execute('''CREATE TABLE IF NOT EXISTS client_group_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        date_added TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES client_groups(id) ON DELETE CASCADE,
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
        UNIQUE(group_id, client_id)
    )''')
    
    # ==================== NOUVELLES TABLES V8 ====================
    
    # Table devis
    c.execute('''CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        date_quote TEXT DEFAULT CURRENT_TIMESTAMP,
        date_validity TEXT,
        status TEXT DEFAULT 'brouillon',
        subtotal REAL DEFAULT 0,
        tgc_rate TEXT DEFAULT 'normal',
        tgc_amount REAL DEFAULT 0,
        total REAL DEFAULT 0,
        notes TEXT,
        conditions TEXT,
        date_created TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )''')
    
    # Table lignes de devis
    c.execute('''CREATE TABLE IF NOT EXISTS quote_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_id INTEGER NOT NULL,
        product_id INTEGER,
        description TEXT NOT NULL,
        quantity REAL DEFAULT 1,
        unit_price REAL DEFAULT 0,
        discount_percent REAL DEFAULT 0,
        total REAL DEFAULT 0,
        position INTEGER DEFAULT 0,
        FOREIGN KEY (quote_id) REFERENCES quotes(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    
    # Table factures
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT UNIQUE NOT NULL,
        quote_id INTEGER,
        client_id INTEGER NOT NULL,
        date_invoice TEXT DEFAULT CURRENT_TIMESTAMP,
        date_due TEXT,
        status TEXT DEFAULT 'brouillon',
        subtotal REAL DEFAULT 0,
        tgc_rate TEXT DEFAULT 'normal',
        tgc_amount REAL DEFAULT 0,
        total REAL DEFAULT 0,
        amount_paid REAL DEFAULT 0,
        notes TEXT,
        conditions TEXT,
        date_created TEXT DEFAULT CURRENT_TIMESTAMP,
        date_paid TEXT,
        FOREIGN KEY (quote_id) REFERENCES quotes(id),
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )''')
    
    # Table lignes de factures
    c.execute('''CREATE TABLE IF NOT EXISTS invoice_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        product_id INTEGER,
        description TEXT NOT NULL,
        quantity REAL DEFAULT 1,
        unit_price REAL DEFAULT 0,
        discount_percent REAL DEFAULT 0,
        total REAL DEFAULT 0,
        position INTEGER DEFAULT 0,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')
    
    # Table ventes caisse
    c.execute('''CREATE TABLE IF NOT EXISTS caisse_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        client_id INTEGER NOT NULL,
        date_sale TEXT DEFAULT CURRENT_TIMESTAMP,
        subtotal REAL DEFAULT 0,
        tgc_amount REAL DEFAULT 0,
        total REAL DEFAULT 0,
        payment_method TEXT DEFAULT 'espèces',
        ticket_z_id INTEGER,
        notes TEXT,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (ticket_z_id) REFERENCES tickets_z(id)
    )''')
    
    # Table tickets Z (clôtures de caisse)
    c.execute('''CREATE TABLE IF NOT EXISTS tickets_z (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number INTEGER NOT NULL,
        date_open TEXT NOT NULL,
        date_close TEXT DEFAULT CURRENT_TIMESTAMP,
        nb_sales INTEGER DEFAULT 0,
        total_especes REAL DEFAULT 0,
        total_carte REAL DEFAULT 0,
        total_autre REAL DEFAULT 0,
        total_ht REAL DEFAULT 0,
        total_tgc REAL DEFAULT 0,
        total_ttc REAL DEFAULT 0,
        closed INTEGER DEFAULT 0,
        objectif_ca REAL DEFAULT 0,
        notes TEXT
    )''')
    
    # Table journées de caisse (objectifs quotidiens)
    c.execute('''CREATE TABLE IF NOT EXISTS caisse_journees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_journee TEXT UNIQUE NOT NULL,
        objectif_ca REAL DEFAULT 0,
        ouvert INTEGER DEFAULT 1,
        notes TEXT
    )''')
    
    # Table interactions CRM
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        subject TEXT,
        content TEXT,
        date_interaction TEXT DEFAULT CURRENT_TIMESTAMP,
        duration_minutes INTEGER,
        followup_date TEXT,
        followup_done INTEGER DEFAULT 0,
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
    )''')
    
    # Table tâches/rappels
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT,
        priority TEXT DEFAULT 'normale',
        status TEXT DEFAULT 'à faire',
        reminder_date TEXT,
        date_created TEXT DEFAULT CURRENT_TIMESTAMP,
        date_completed TEXT,
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
    )''')
    
    # Table emails programmés
    c.execute('''CREATE TABLE IF NOT EXISTS scheduled_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER,
        recipient_filter TEXT,
        recipient_group_id INTEGER,
        subject TEXT NOT NULL,
        content_json TEXT,
        scheduled_date TEXT NOT NULL,
        status TEXT DEFAULT 'programmé',
        sent_count INTEGER DEFAULT 0,
        date_created TEXT DEFAULT CURRENT_TIMESTAMP,
        date_sent TEXT,
        FOREIGN KEY (template_id) REFERENCES email_templates(id),
        FOREIGN KEY (recipient_group_id) REFERENCES client_groups(id)
    )''')
    
    # Table séquences emails automatiques
    c.execute('''CREATE TABLE IF NOT EXISTS email_sequences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        trigger_event TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        date_created TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table étapes des séquences
    c.execute('''CREATE TABLE IF NOT EXISTS email_sequence_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sequence_id INTEGER NOT NULL,
        step_order INTEGER NOT NULL,
        delay_days INTEGER DEFAULT 0,
        delay_hours INTEGER DEFAULT 0,
        template_id INTEGER,
        subject TEXT,
        content_json TEXT,
        FOREIGN KEY (sequence_id) REFERENCES email_sequences(id) ON DELETE CASCADE,
        FOREIGN KEY (template_id) REFERENCES email_templates(id)
    )''')
    
    # Table historique des séquences envoyées
    c.execute('''CREATE TABLE IF NOT EXISTS email_sequence_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sequence_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        current_step INTEGER DEFAULT 0,
        status TEXT DEFAULT 'en_cours',
        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
        next_send_at TEXT,
        completed_at TEXT,
        FOREIGN KEY (sequence_id) REFERENCES email_sequences(id),
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
    )''')
    
    # Table compteurs pour numérotation
    c.execute('''CREATE TABLE IF NOT EXISTS counters (
        name TEXT PRIMARY KEY,
        value INTEGER DEFAULT 0,
        year INTEGER
    )''')
    
    # ==================== FIN NOUVELLES TABLES ====================
    
    # Migrations colonnes manquantes
    migrations = [
        ("clients", "dette_m1", "REAL DEFAULT 0"),
        ("clients", "dette_m2", "REAL DEFAULT 0"),
        ("clients", "dette_m3", "REAL DEFAULT 0"),
        ("clients", "dette_m3plus", "REAL DEFAULT 0"),
        ("clients", "dernier_rappel", "TEXT"),
        ("clients", "newsletter", "INTEGER DEFAULT 1"),
        ("clients", "client_type", "TEXT DEFAULT 'particulier'"),
        ("clients", "ridet", "TEXT"),
        ("clients", "forme_juridique", "TEXT"),
        ("clients", "nom_gerant", "TEXT"),
        ("clients", "bloque", "INTEGER DEFAULT 0"),
        ("clients", "motif_blocage", "TEXT"),
        ("clients", "date_blocage", "TEXT"),
        ("clients", "date_dette_m1", "TEXT"),
        ("clients", "date_dette_m2", "TEXT"),
        ("clients", "date_dette_m3", "TEXT"),
        ("clients", "code_parrainage", "TEXT"),  # Code unique pour parrainage
        ("clients", "parraine_par", "INTEGER"),  # ID du parrain
        ("clients", "is_prospect", "INTEGER DEFAULT 0"),  # Prospect ou client
        ("products", "cost", "REAL DEFAULT 0"),
        ("products", "active", "INTEGER DEFAULT 1"),
        ("products", "image_url", "TEXT"),
        ("products", "image_url_2", "TEXT"),
        ("products", "image_url_3", "TEXT"),
        ("products", "prix_particulier", "REAL DEFAULT 0"),  # Prix pour particuliers
        ("products", "prix_pro", "REAL DEFAULT 0"),  # Prix pour professionnels
        ("depots", "client_id", "INTEGER"),
        ("depot_products", "discount_percent", "REAL DEFAULT 0"),
    ]
    for table, col, col_type in migrations:
        try:
            c.execute(f"SELECT {col} FROM {table} LIMIT 1")
        except sqlite3.OperationalError:
            try: c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"); conn.commit()
            except: pass
    
    # Migration: copier price vers prix_particulier et prix_pro si vides
    try:
        c.execute("""UPDATE products SET prix_particulier = price 
                     WHERE (prix_particulier IS NULL OR prix_particulier = 0) AND price > 0""")
        c.execute("""UPDATE products SET prix_pro = price 
                     WHERE (prix_pro IS NULL OR prix_pro = 0) AND price > 0""")
        conn.commit()
    except: pass
    
    # Générer les codes parrainage manquants
    c.execute("SELECT id, name FROM clients WHERE code_parrainage IS NULL OR code_parrainage = ''")
    clients_sans_code = c.fetchall()
    for client_id, name in clients_sans_code:
        code = generate_parrainage_code(name, client_id)
        c.execute("UPDATE clients SET code_parrainage = ? WHERE id = ?", (code, client_id))
    
    # Créer le client comptoir par défaut (code 9900) s'il n'existe pas
    client_comptoir = c.execute("SELECT id FROM clients WHERE code_parrainage = 'COMPTOIR9900'").fetchone()
    if not client_comptoir:
        c.execute("""INSERT INTO clients (name, email, phone, client_type, newsletter, code_parrainage, notes)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  ("Client Comptoir", "", "", "particulier", 0, "COMPTOIR9900",
                   "Client par défaut pour les ventes au comptoir sans identification"))
        print("[INIT] Client Comptoir créé (code 9900)")
    
    conn.commit()
    conn.close()


# Code client comptoir
CLIENT_COMPTOIR_CODE = "COMPTOIR9900"


def get_client_comptoir():
    """Récupère ou crée le client comptoir."""
    conn = get_connection()
    client = conn.execute("SELECT * FROM clients WHERE code_parrainage = ?", (CLIENT_COMPTOIR_CODE,)).fetchone()
    conn.close()
    return client


# ============================================================================
# FONCTIONS CAISSE - VENTES ET TICKETS Z
# ============================================================================

def save_caisse_sale(data, invoice_id=None):
    """Enregistre une vente de caisse."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""INSERT INTO caisse_sales (invoice_id, client_id, subtotal, tgc_amount, total, payment_method, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (invoice_id, data['client_id'], data['subtotal'], data['tgc_amount'], 
               data['total'], data['payment_method'], data.get('notes', '')))
    sale_id = c.lastrowid
    conn.commit()
    conn.close()
    return sale_id


def get_caisse_sales_today():
    """Récupère les ventes du jour non clôturées."""
    conn = get_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    sales = conn.execute("""
        SELECT cs.*, c.name as client_name, i.number as invoice_number
        FROM caisse_sales cs
        LEFT JOIN clients c ON cs.client_id = c.id
        LEFT JOIN invoices i ON cs.invoice_id = i.id
        WHERE DATE(cs.date_sale) = ? AND cs.ticket_z_id IS NULL
        ORDER BY cs.date_sale DESC
    """, (today,)).fetchall()
    conn.close()
    return sales


def get_caisse_sales_by_period(date_start, date_end=None):
    """Récupère les ventes sur une période."""
    conn = get_connection()
    if date_end is None:
        date_end = date_start
    sales = conn.execute("""
        SELECT cs.*, c.name as client_name, i.number as invoice_number
        FROM caisse_sales cs
        LEFT JOIN clients c ON cs.client_id = c.id
        LEFT JOIN invoices i ON cs.invoice_id = i.id
        WHERE DATE(cs.date_sale) BETWEEN ? AND ?
        ORDER BY cs.date_sale DESC
    """, (date_start, date_end)).fetchall()
    conn.close()
    return sales


def get_caisse_sales_by_ticket_z(ticket_z_id):
    """Récupère les ventes d'un ticket Z."""
    conn = get_connection()
    sales = conn.execute("""
        SELECT cs.*, c.name as client_name, i.number as invoice_number
        FROM caisse_sales cs
        LEFT JOIN clients c ON cs.client_id = c.id
        LEFT JOIN invoices i ON cs.invoice_id = i.id
        WHERE cs.ticket_z_id = ?
        ORDER BY cs.date_sale ASC
    """, (ticket_z_id,)).fetchall()
    conn.close()
    return sales


def get_all_caisse_sales(limit=100):
    """Récupère toutes les ventes de caisse."""
    conn = get_connection()
    sales = conn.execute("""
        SELECT cs.*, c.name as client_name, i.number as invoice_number, 
               tz.number as ticket_z_number
        FROM caisse_sales cs
        LEFT JOIN clients c ON cs.client_id = c.id
        LEFT JOIN invoices i ON cs.invoice_id = i.id
        LEFT JOIN tickets_z tz ON cs.ticket_z_id = tz.id
        ORDER BY cs.date_sale DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return sales


def get_next_ticket_z_number():
    """Retourne le prochain numéro de ticket Z."""
    conn = get_connection()
    result = conn.execute("SELECT MAX(number) FROM tickets_z").fetchone()
    conn.close()
    return (result[0] or 0) + 1


def create_ticket_z(date_open=None):
    """Crée un nouveau ticket Z (ouverture de caisse)."""
    conn = get_connection()
    c = conn.cursor()
    number = get_next_ticket_z_number()
    if date_open is None:
        date_open = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("""INSERT INTO tickets_z (number, date_open, closed) VALUES (?, ?, 0)""",
              (number, date_open))
    ticket_id = c.lastrowid
    conn.commit()
    conn.close()
    return ticket_id, number


def close_ticket_z(notes=""):
    """Clôture le ticket Z du jour (génère le rapport Z)."""
    conn = get_connection()
    c = conn.cursor()
    
    # Récupérer les ventes non clôturées
    sales = conn.execute("""
        SELECT id, subtotal, tgc_amount, total, payment_method 
        FROM caisse_sales WHERE ticket_z_id IS NULL
    """).fetchall()
    
    if not sales:
        conn.close()
        return None, "Aucune vente à clôturer"
    
    # Calculer les totaux
    total_especes = 0
    total_carte = 0
    total_autre = 0
    total_ht = 0
    total_tgc = 0
    total_ttc = 0
    
    sale_ids = []
    for sale in sales:
        sale_ids.append(sale['id'])
        total_ht += sale['subtotal'] or 0
        total_tgc += sale['tgc_amount'] or 0
        total_ttc += sale['total'] or 0
        
        payment = sale['payment_method'] or 'espèces'
        if payment == 'espèces':
            total_especes += sale['total'] or 0
        elif payment == 'carte':
            total_carte += sale['total'] or 0
        else:
            total_autre += sale['total'] or 0
    
    # Trouver la date d'ouverture (première vente)
    first_sale = conn.execute("""
        SELECT MIN(date_sale) FROM caisse_sales WHERE ticket_z_id IS NULL
    """).fetchone()
    date_open = first_sale[0] if first_sale else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Créer le ticket Z
    number = get_next_ticket_z_number()
    c.execute("""INSERT INTO tickets_z 
                 (number, date_open, nb_sales, total_especes, total_carte, total_autre,
                  total_ht, total_tgc, total_ttc, closed, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
              (number, date_open, len(sales), total_especes, total_carte, total_autre,
               total_ht, total_tgc, total_ttc, notes))
    ticket_id = c.lastrowid
    
    # Associer les ventes au ticket Z
    for sale_id in sale_ids:
        c.execute("UPDATE caisse_sales SET ticket_z_id = ? WHERE id = ?", (ticket_id, sale_id))
    
    conn.commit()
    conn.close()
    
    return ticket_id, {
        'number': number,
        'nb_sales': len(sales),
        'total_especes': total_especes,
        'total_carte': total_carte,
        'total_autre': total_autre,
        'total_ht': total_ht,
        'total_tgc': total_tgc,
        'total_ttc': total_ttc
    }


def get_ticket_z(ticket_id):
    """Récupère un ticket Z par son ID."""
    conn = get_connection()
    ticket = conn.execute("SELECT * FROM tickets_z WHERE id = ?", (ticket_id,)).fetchone()
    conn.close()
    return ticket


def get_all_tickets_z(limit=50):
    """Récupère tous les tickets Z."""
    conn = get_connection()
    tickets = conn.execute("""
        SELECT * FROM tickets_z WHERE closed = 1 ORDER BY date_close DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return tickets


def get_caisse_stats_today():
    """Statistiques de caisse du jour."""
    conn = get_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    
    stats = {
        'nb_sales': 0,
        'total_especes': 0,
        'total_carte': 0,
        'total_autre': 0,
        'total_ttc': 0,
        'objectif_ca': 0,
        'progression': 0
    }
    
    result = conn.execute("""
        SELECT COUNT(*), 
               SUM(CASE WHEN payment_method = 'espèces' THEN total ELSE 0 END),
               SUM(CASE WHEN payment_method = 'carte' THEN total ELSE 0 END),
               SUM(CASE WHEN payment_method = 'autre' THEN total ELSE 0 END),
               SUM(total)
        FROM caisse_sales 
        WHERE DATE(date_sale) = ? AND ticket_z_id IS NULL
    """, (today,)).fetchone()
    
    if result:
        stats['nb_sales'] = result[0] or 0
        stats['total_especes'] = result[1] or 0
        stats['total_carte'] = result[2] or 0
        stats['total_autre'] = result[3] or 0
        stats['total_ttc'] = result[4] or 0
    
    # Récupérer l'objectif du jour
    journee = conn.execute("SELECT objectif_ca FROM caisse_journees WHERE date_journee = ?", (today,)).fetchone()
    if journee and journee['objectif_ca']:
        stats['objectif_ca'] = journee['objectif_ca']
        if stats['objectif_ca'] > 0:
            stats['progression'] = min(100, (stats['total_ttc'] / stats['objectif_ca']) * 100)
    
    conn.close()
    return stats


def get_or_create_journee_caisse(date=None):
    """Récupère ou crée la journée de caisse."""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_connection()
    journee = conn.execute("SELECT * FROM caisse_journees WHERE date_journee = ?", (date,)).fetchone()
    
    if not journee:
        conn.execute("INSERT INTO caisse_journees (date_journee, objectif_ca) VALUES (?, 0)", (date,))
        conn.commit()
        journee = conn.execute("SELECT * FROM caisse_journees WHERE date_journee = ?", (date,)).fetchone()
    
    conn.close()
    return journee


def set_objectif_ca(objectif, date=None):
    """Définit l'objectif CA du jour."""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_connection()
    
    # Vérifier si la journée existe
    journee = conn.execute("SELECT id FROM caisse_journees WHERE date_journee = ?", (date,)).fetchone()
    
    if journee:
        conn.execute("UPDATE caisse_journees SET objectif_ca = ? WHERE date_journee = ?", (objectif, date))
    else:
        conn.execute("INSERT INTO caisse_journees (date_journee, objectif_ca) VALUES (?, ?)", (date, objectif))
    
    conn.commit()
    conn.close()
    return True


def get_objectif_ca(date=None):
    """Récupère l'objectif CA du jour."""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_connection()
    result = conn.execute("SELECT objectif_ca FROM caisse_journees WHERE date_journee = ?", (date,)).fetchone()
    conn.close()
    
    return result['objectif_ca'] if result else 0


def generate_parrainage_code(name, client_id):
    """Génère un code parrainage unique basé sur le nom et l'ID."""
    import hashlib
    # Prendre les 3 premières lettres du nom (sans accents, majuscules)
    prefix = ''.join(c for c in name.upper()[:3] if c.isalpha())
    if len(prefix) < 3:
        prefix = prefix + "X" * (3 - len(prefix))
    # Ajouter un hash court basé sur l'ID
    hash_part = hashlib.md5(f"{client_id}{name}".encode()).hexdigest()[:4].upper()
    return f"{prefix}{hash_part}"


# ============================================================================
# FONCTIONS CRUD
# ============================================================================
# Clients
def get_all_clients(newsletter_only=False, client_type=None, with_debt=False):
    conn = get_connection()
    query = "SELECT * FROM clients WHERE 1=1"
    params = []
    if newsletter_only: query += " AND newsletter=1"
    if client_type: query += " AND client_type=?"; params.append(client_type)
    if with_debt: query += " AND (dette_m1>0 OR dette_m2>0 OR dette_m3>0 OR dette_m3plus>0)"
    query += " ORDER BY name"
    clients = conn.execute(query, params).fetchall()
    conn.close()
    return clients

def get_client(client_id):
    conn = get_connection()
    client = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    return client

def save_client(data, client_id=None):
    conn = get_connection()
    c = conn.cursor()
    
    # Gérer les dates de dette automatiquement
    now = datetime.now().isoformat()
    
    if client_id:
        # Récupérer l'ancien client pour comparer
        old = c.execute("SELECT dette_m1, date_dette_m1 FROM clients WHERE id=?", (client_id,)).fetchone()
        old_m1 = old[0] if old else 0
        old_date_m1 = old[1] if old else None
        
        # Si M1 change et devient > 0, mettre à jour la date
        new_m1 = data.get('dette_m1', 0)
        if new_m1 > 0 and (old_m1 == 0 or old_m1 is None):
            data['date_dette_m1'] = now
        elif new_m1 == 0:
            data['date_dette_m1'] = None
        else:
            data['date_dette_m1'] = old_date_m1
        
        c.execute("""UPDATE clients SET name=?, email=?, phone=?, address=?, client_type=?, 
                     newsletter=?, is_prospect=?, notes=?, ridet=?, forme_juridique=?, nom_gerant=?,
                     bloque=?, motif_blocage=?, date_blocage=?,
                     dette_m1=?, dette_m2=?, dette_m3=?, dette_m3plus=?, date_dette_m1=? WHERE id=?""",
                  (data['name'], data.get('email'), data.get('phone'), data.get('address'),
                   data.get('client_type', 'particulier'), data.get('newsletter', 1), 
                   1 if data.get('is_prospect') else 0, data.get('notes'),
                   data.get('ridet'), data.get('forme_juridique'), data.get('nom_gerant'),
                   data.get('bloque', 0), data.get('motif_blocage'), data.get('date_blocage'),
                   data.get('dette_m1', 0), data.get('dette_m2', 0), data.get('dette_m3', 0),
                   data.get('dette_m3plus', 0), data.get('date_dette_m1'), client_id))
    else:
        date_m1 = now if data.get('dette_m1', 0) > 0 else None
        c.execute("""INSERT INTO clients (name, email, phone, address, client_type, newsletter, is_prospect, notes,
                     ridet, forme_juridique, nom_gerant, bloque, motif_blocage, date_blocage,
                     dette_m1, dette_m2, dette_m3, dette_m3plus, date_dette_m1) 
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (data['name'], data.get('email'), data.get('phone'), data.get('address'),
                   data.get('client_type', 'particulier'), data.get('newsletter', 1), 
                   1 if data.get('is_prospect') else 0, data.get('notes'),
                   data.get('ridet'), data.get('forme_juridique'), data.get('nom_gerant'),
                   data.get('bloque', 0), data.get('motif_blocage'), data.get('date_blocage'),
                   data.get('dette_m1', 0), data.get('dette_m2', 0), data.get('dette_m3', 0),
                   data.get('dette_m3plus', 0), date_m1))
        client_id = c.lastrowid
        
        # Générer le code parrainage unique
        code_parrainage = generate_parrainage_code(data['name'], client_id)
        c.execute("UPDATE clients SET code_parrainage = ? WHERE id = ?", (code_parrainage, client_id))
    
    conn.commit()
    conn.close()
    return client_id


def get_client_parrainage_code(client_id):
    """Récupère le code parrainage d'un client."""
    conn = get_connection()
    result = conn.execute("SELECT code_parrainage FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    return result[0] if result else None


def get_clients_by_group(group_id):
    """Récupère tous les clients d'un groupe."""
    conn = get_connection()
    clients = conn.execute("""
        SELECT c.* FROM clients c
        INNER JOIN client_group_members m ON c.id = m.client_id
        WHERE m.group_id = ?
        ORDER BY c.name
    """, (group_id,)).fetchall()
    conn.close()
    return clients


def get_or_create_prospects_group():
    """Récupère ou crée le groupe Prospects automatique."""
    conn = get_connection()
    c = conn.cursor()
    
    # Chercher le groupe Prospects
    group = c.execute("SELECT id FROM client_groups WHERE name = 'Prospects'").fetchone()
    
    if group:
        group_id = group[0]
    else:
        # Créer le groupe Prospects
        c.execute("""INSERT INTO client_groups (name, description, color) 
                     VALUES (?, ?, ?)""",
                  ("Prospects", "Groupe automatique des prospects (non clients)", "#f39c12"))
        group_id = c.lastrowid
        conn.commit()
    
    conn.close()
    return group_id


def manage_prospect_group(client_id, is_prospect):
    """Ajoute ou retire un client du groupe Prospects selon son statut."""
    prospects_group_id = get_or_create_prospects_group()
    
    conn = get_connection()
    c = conn.cursor()
    
    # Vérifier si le client est déjà dans le groupe
    existing = c.execute("""SELECT id FROM client_group_members 
                            WHERE group_id = ? AND client_id = ?""",
                         (prospects_group_id, client_id)).fetchone()
    
    if is_prospect and not existing:
        # Ajouter au groupe Prospects
        try:
            c.execute("""INSERT INTO client_group_members (group_id, client_id) VALUES (?, ?)""",
                      (prospects_group_id, client_id))
        except:
            pass  # Déjà présent
    elif not is_prospect and existing:
        # Retirer du groupe Prospects
        c.execute("""DELETE FROM client_group_members 
                     WHERE group_id = ? AND client_id = ?""",
                  (prospects_group_id, client_id))
    
    conn.commit()
    conn.close()


def get_all_prospects():
    """Récupère tous les prospects."""
    conn = get_connection()
    clients = conn.execute("SELECT * FROM clients WHERE is_prospect = 1 ORDER BY name").fetchall()
    conn.close()
    return clients


# ============================================================================
# FONCTIONS DEVIS & FACTURES
# ============================================================================
def get_next_number(prefix):
    """Génère le prochain numéro de devis ou facture."""
    conn = get_connection()
    c = conn.cursor()
    year = datetime.now().year
    
    # Vérifier/créer le compteur
    counter = c.execute("SELECT value, year FROM counters WHERE name=?", (prefix,)).fetchone()
    
    if counter and counter[1] == year:
        new_value = counter[0] + 1
        c.execute("UPDATE counters SET value=? WHERE name=?", (new_value, prefix))
    else:
        new_value = 1
        c.execute("INSERT OR REPLACE INTO counters (name, value, year) VALUES (?, ?, ?)", 
                  (prefix, new_value, year))
    
    conn.commit()
    conn.close()
    return f"{prefix}{year}-{new_value:04d}"


def get_all_quotes(client_id=None, status=None):
    """Récupère tous les devis."""
    conn = get_connection()
    query = "SELECT q.*, c.name as client_name FROM quotes q LEFT JOIN clients c ON q.client_id = c.id WHERE 1=1"
    params = []
    if client_id: query += " AND q.client_id=?"; params.append(client_id)
    if status: query += " AND q.status=?"; params.append(status)
    query += " ORDER BY q.date_created DESC"
    quotes = conn.execute(query, params).fetchall()
    conn.close()
    return quotes


def get_quote(quote_id):
    """Récupère un devis avec ses lignes."""
    conn = get_connection()
    quote = conn.execute("""SELECT q.*, c.name as client_name, c.email as client_email, 
                            c.address as client_address, c.phone as client_phone, c.ridet as client_ridet
                            FROM quotes q LEFT JOIN clients c ON q.client_id = c.id 
                            WHERE q.id=?""", (quote_id,)).fetchone()
    if quote:
        lines = conn.execute("""SELECT ql.*, p.name as product_name 
                                FROM quote_lines ql LEFT JOIN products p ON ql.product_id = p.id
                                WHERE ql.quote_id=? ORDER BY ql.position""", (quote_id,)).fetchall()
    else:
        lines = []
    conn.close()
    return quote, lines


def save_quote(data, lines, quote_id=None):
    """Sauvegarde un devis."""
    conn = get_connection()
    c = conn.cursor()
    
    # Calculer les totaux
    subtotal = sum(l.get('total', 0) for l in lines)
    tgc_rate = data.get('tgc_rate', DEFAULT_TGC_RATE)
    tgc_percent = TGC_RATES.get(tgc_rate, 11)
    tgc_amount = subtotal * tgc_percent / 100
    total = subtotal + tgc_amount
    
    if quote_id:
        c.execute("""UPDATE quotes SET client_id=?, date_validity=?, status=?, 
                     subtotal=?, tgc_rate=?, tgc_amount=?, total=?, notes=?, conditions=?
                     WHERE id=?""",
                  (data['client_id'], data.get('date_validity'), data.get('status', 'brouillon'),
                   subtotal, tgc_rate, tgc_amount, total, data.get('notes'), data.get('conditions'),
                   quote_id))
        # Supprimer les anciennes lignes
        c.execute("DELETE FROM quote_lines WHERE quote_id=?", (quote_id,))
    else:
        number = get_next_number(QUOTE_PREFIX)
        c.execute("""INSERT INTO quotes (number, client_id, date_validity, status,
                     subtotal, tgc_rate, tgc_amount, total, notes, conditions)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (number, data['client_id'], data.get('date_validity'), data.get('status', 'brouillon'),
                   subtotal, tgc_rate, tgc_amount, total, data.get('notes'), data.get('conditions')))
        quote_id = c.lastrowid
    
    # Ajouter les lignes
    for i, line in enumerate(lines):
        line_total = line.get('quantity', 1) * line.get('unit_price', 0) * (1 - line.get('discount_percent', 0) / 100)
        c.execute("""INSERT INTO quote_lines (quote_id, product_id, description, quantity, 
                     unit_price, discount_percent, total, position)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (quote_id, line.get('product_id'), line['description'], line.get('quantity', 1),
                   line.get('unit_price', 0), line.get('discount_percent', 0), line_total, i))
    
    conn.commit()
    conn.close()
    return quote_id


def delete_quote(quote_id):
    conn = get_connection()
    conn.execute("DELETE FROM quotes WHERE id=?", (quote_id,))
    conn.commit()
    conn.close()


def convert_quote_to_invoice(quote_id):
    """Convertit un devis en facture."""
    quote, lines = get_quote(quote_id)
    if not quote: return None
    
    conn = get_connection()
    c = conn.cursor()
    
    number = get_next_number(INVOICE_PREFIX)
    due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    c.execute("""INSERT INTO invoices (number, quote_id, client_id, date_due, status,
                 subtotal, tgc_rate, tgc_amount, total, notes, conditions)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (number, quote_id, quote['client_id'], due_date, 'envoyée',
               quote['subtotal'], quote['tgc_rate'], quote['tgc_amount'], quote['total'],
               quote['notes'], quote['conditions']))
    invoice_id = c.lastrowid
    
    # Copier les lignes
    for line in lines:
        c.execute("""INSERT INTO invoice_lines (invoice_id, product_id, description, quantity,
                     unit_price, discount_percent, total, position)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (invoice_id, line['product_id'], line['description'], line['quantity'],
                   line['unit_price'], line['discount_percent'], line['total'], line['position']))
    
    # Marquer le devis comme accepté
    c.execute("UPDATE quotes SET status='accepté' WHERE id=?", (quote_id,))
    
    conn.commit()
    conn.close()
    return invoice_id


def get_all_invoices(client_id=None, status=None):
    """Récupère toutes les factures."""
    conn = get_connection()
    query = "SELECT i.*, c.name as client_name FROM invoices i LEFT JOIN clients c ON i.client_id = c.id WHERE 1=1"
    params = []
    if client_id: query += " AND i.client_id=?"; params.append(client_id)
    if status: query += " AND i.status=?"; params.append(status)
    query += " ORDER BY i.date_created DESC"
    invoices = conn.execute(query, params).fetchall()
    conn.close()
    return invoices


def get_invoice(invoice_id):
    """Récupère une facture avec ses lignes."""
    conn = get_connection()
    invoice = conn.execute("""SELECT i.*, c.name as client_name, c.email as client_email,
                              c.address as client_address, c.phone as client_phone, c.ridet as client_ridet
                              FROM invoices i LEFT JOIN clients c ON i.client_id = c.id
                              WHERE i.id=?""", (invoice_id,)).fetchone()
    if invoice:
        lines = conn.execute("""SELECT il.*, p.name as product_name
                                FROM invoice_lines il LEFT JOIN products p ON il.product_id = p.id
                                WHERE il.invoice_id=? ORDER BY il.position""", (invoice_id,)).fetchall()
    else:
        lines = []
    conn.close()
    return invoice, lines


def save_invoice(data, lines, invoice_id=None):
    """Sauvegarde une facture."""
    conn = get_connection()
    c = conn.cursor()
    
    subtotal = sum(l.get('total', 0) for l in lines)
    tgc_rate = data.get('tgc_rate', DEFAULT_TGC_RATE)
    tgc_percent = TGC_RATES.get(tgc_rate, 11)
    tgc_amount = subtotal * tgc_percent / 100
    total = subtotal + tgc_amount
    
    if invoice_id:
        c.execute("""UPDATE invoices SET client_id=?, date_due=?, status=?,
                     subtotal=?, tgc_rate=?, tgc_amount=?, total=?, 
                     amount_paid=?, notes=?, conditions=?, date_paid=?
                     WHERE id=?""",
                  (data['client_id'], data.get('date_due'), data.get('status', 'brouillon'),
                   subtotal, tgc_rate, tgc_amount, total,
                   data.get('amount_paid', 0), data.get('notes'), data.get('conditions'),
                   data.get('date_paid'), invoice_id))
        c.execute("DELETE FROM invoice_lines WHERE invoice_id=?", (invoice_id,))
    else:
        number = get_next_number(INVOICE_PREFIX)
        c.execute("""INSERT INTO invoices (number, client_id, date_due, status,
                     subtotal, tgc_rate, tgc_amount, total, notes, conditions)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (number, data['client_id'], data.get('date_due'), data.get('status', 'brouillon'),
                   subtotal, tgc_rate, tgc_amount, total, data.get('notes'), data.get('conditions')))
        invoice_id = c.lastrowid
    
    for i, line in enumerate(lines):
        line_total = line.get('quantity', 1) * line.get('unit_price', 0) * (1 - line.get('discount_percent', 0) / 100)
        c.execute("""INSERT INTO invoice_lines (invoice_id, product_id, description, quantity,
                     unit_price, discount_percent, total, position)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (invoice_id, line.get('product_id'), line['description'], line.get('quantity', 1),
                   line.get('unit_price', 0), line.get('discount_percent', 0), line_total, i))
    
    conn.commit()
    conn.close()
    return invoice_id


def delete_invoice(invoice_id):
    conn = get_connection()
    conn.execute("DELETE FROM invoices WHERE id=?", (invoice_id,))
    conn.commit()
    conn.close()


def mark_invoice_paid(invoice_id, amount=None, date_paid=None):
    """Marque une facture comme payée."""
    conn = get_connection()
    invoice = conn.execute("SELECT total FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if invoice:
        paid_amount = amount if amount else invoice['total']
        paid_date = date_paid if date_paid else datetime.now().strftime('%Y-%m-%d')
        conn.execute("""UPDATE invoices SET status='payée', amount_paid=?, date_paid=? WHERE id=?""",
                     (paid_amount, paid_date, invoice_id))
        conn.commit()
    conn.close()


# ============================================================================
# FONCTIONS CRM - INTERACTIONS
# ============================================================================
def get_all_interactions(client_id=None, limit=100):
    """Récupère les interactions."""
    conn = get_connection()
    query = """SELECT i.*, c.name as client_name 
               FROM interactions i LEFT JOIN clients c ON i.client_id = c.id WHERE 1=1"""
    params = []
    if client_id: query += " AND i.client_id=?"; params.append(client_id)
    query += f" ORDER BY i.date_interaction DESC LIMIT {limit}"
    interactions = conn.execute(query, params).fetchall()
    conn.close()
    return interactions


def save_interaction(data, interaction_id=None):
    """Sauvegarde une interaction."""
    conn = get_connection()
    c = conn.cursor()
    
    if interaction_id:
        c.execute("""UPDATE interactions SET client_id=?, type=?, subject=?, content=?,
                     date_interaction=?, duration_minutes=?, followup_date=?, followup_done=?
                     WHERE id=?""",
                  (data['client_id'], data['type'], data.get('subject'), data.get('content'),
                   data.get('date_interaction', datetime.now().isoformat()), data.get('duration_minutes'),
                   data.get('followup_date'), data.get('followup_done', 0), interaction_id))
    else:
        c.execute("""INSERT INTO interactions (client_id, type, subject, content,
                     date_interaction, duration_minutes, followup_date)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (data['client_id'], data['type'], data.get('subject'), data.get('content'),
                   data.get('date_interaction', datetime.now().isoformat()), data.get('duration_minutes'),
                   data.get('followup_date')))
        interaction_id = c.lastrowid
    
    conn.commit()
    conn.close()
    return interaction_id


def delete_interaction(interaction_id):
    conn = get_connection()
    conn.execute("DELETE FROM interactions WHERE id=?", (interaction_id,))
    conn.commit()
    conn.close()


# ============================================================================
# FONCTIONS CRM - TÂCHES
# ============================================================================
def get_all_tasks(status=None, client_id=None, include_completed=False):
    """Récupère les tâches."""
    conn = get_connection()
    query = """SELECT t.*, c.name as client_name 
               FROM tasks t LEFT JOIN clients c ON t.client_id = c.id WHERE 1=1"""
    params = []
    if client_id: query += " AND t.client_id=?"; params.append(client_id)
    if status: query += " AND t.status=?"; params.append(status)
    if not include_completed: query += " AND t.status != 'terminée'"
    query += " ORDER BY CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END, t.due_date ASC"
    tasks = conn.execute(query, params).fetchall()
    conn.close()
    return tasks


def get_tasks_due_today():
    """Récupère les tâches dues aujourd'hui."""
    conn = get_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    tasks = conn.execute("""SELECT t.*, c.name as client_name 
                            FROM tasks t LEFT JOIN clients c ON t.client_id = c.id
                            WHERE t.due_date <= ? AND t.status != 'terminée'
                            ORDER BY t.priority DESC, t.due_date""", (today,)).fetchall()
    conn.close()
    return tasks


def save_task(data, task_id=None):
    """Sauvegarde une tâche."""
    conn = get_connection()
    c = conn.cursor()
    
    if task_id:
        c.execute("""UPDATE tasks SET client_id=?, title=?, description=?, due_date=?,
                     priority=?, status=?, reminder_date=?, date_completed=?
                     WHERE id=?""",
                  (data.get('client_id'), data['title'], data.get('description'), data.get('due_date'),
                   data.get('priority', 'normale'), data.get('status', 'à faire'),
                   data.get('reminder_date'), data.get('date_completed'), task_id))
    else:
        c.execute("""INSERT INTO tasks (client_id, title, description, due_date, priority, status, reminder_date)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (data.get('client_id'), data['title'], data.get('description'), data.get('due_date'),
                   data.get('priority', 'normale'), data.get('status', 'à faire'), data.get('reminder_date')))
        task_id = c.lastrowid
    
    conn.commit()
    conn.close()
    return task_id


def complete_task(task_id):
    """Marque une tâche comme terminée."""
    conn = get_connection()
    conn.execute("UPDATE tasks SET status='terminée', date_completed=? WHERE id=?",
                 (datetime.now().isoformat(), task_id))
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


# ============================================================================
# FONCTIONS EMAILS PROGRAMMÉS
# ============================================================================
def get_scheduled_emails(status=None):
    """Récupère les emails programmés."""
    conn = get_connection()
    query = "SELECT * FROM scheduled_emails WHERE 1=1"
    params = []
    if status: query += " AND status=?"; params.append(status)
    query += " ORDER BY scheduled_date ASC"
    emails = conn.execute(query, params).fetchall()
    conn.close()
    return emails


def save_scheduled_email(data, email_id=None):
    """Programme un email."""
    conn = get_connection()
    c = conn.cursor()
    
    if email_id:
        c.execute("""UPDATE scheduled_emails SET template_id=?, recipient_filter=?, 
                     recipient_group_id=?, subject=?, content_json=?, scheduled_date=?, status=?
                     WHERE id=?""",
                  (data.get('template_id'), data.get('recipient_filter'), data.get('recipient_group_id'),
                   data['subject'], data.get('content_json'), data['scheduled_date'],
                   data.get('status', 'programmé'), email_id))
    else:
        c.execute("""INSERT INTO scheduled_emails (template_id, recipient_filter, recipient_group_id,
                     subject, content_json, scheduled_date)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (data.get('template_id'), data.get('recipient_filter'), data.get('recipient_group_id'),
                   data['subject'], data.get('content_json'), data['scheduled_date']))
        email_id = c.lastrowid
    
    conn.commit()
    conn.close()
    return email_id


def delete_scheduled_email(email_id):
    conn = get_connection()
    conn.execute("DELETE FROM scheduled_emails WHERE id=?", (email_id,))
    conn.commit()
    conn.close()


def check_and_send_scheduled_emails():
    """Vérifie et envoie les emails programmés (à appeler régulièrement)."""
    conn = get_connection()
    now = datetime.now().isoformat()
    
    emails = conn.execute("""SELECT * FROM scheduled_emails 
                             WHERE status='programmé' AND scheduled_date <= ?""", (now,)).fetchall()
    
    for email in emails:
        # Logique d'envoi (simplifiée)
        # TODO: Implémenter l'envoi réel
        conn.execute("UPDATE scheduled_emails SET status='envoyé', date_sent=? WHERE id=?",
                     (now, email['id']))
    
    conn.commit()
    conn.close()
    return len(emails)


# ============================================================================
# FONCTIONS SÉQUENCES EMAILS
# ============================================================================
def get_all_sequences():
    """Récupère toutes les séquences email."""
    conn = get_connection()
    sequences = conn.execute("SELECT * FROM email_sequences ORDER BY name").fetchall()
    conn.close()
    return sequences


def get_sequence_with_steps(sequence_id):
    """Récupère une séquence avec ses étapes."""
    conn = get_connection()
    sequence = conn.execute("SELECT * FROM email_sequences WHERE id=?", (sequence_id,)).fetchone()
    steps = conn.execute("""SELECT * FROM email_sequence_steps 
                            WHERE sequence_id=? ORDER BY step_order""", (sequence_id,)).fetchall()
    conn.close()
    return sequence, steps


def save_sequence(data, steps, sequence_id=None):
    """Sauvegarde une séquence email."""
    conn = get_connection()
    c = conn.cursor()
    
    if sequence_id:
        c.execute("UPDATE email_sequences SET name=?, trigger_event=?, active=? WHERE id=?",
                  (data['name'], data['trigger_event'], data.get('active', 1), sequence_id))
        c.execute("DELETE FROM email_sequence_steps WHERE sequence_id=?", (sequence_id,))
    else:
        c.execute("INSERT INTO email_sequences (name, trigger_event, active) VALUES (?, ?, ?)",
                  (data['name'], data['trigger_event'], data.get('active', 1)))
        sequence_id = c.lastrowid
    
    for i, step in enumerate(steps):
        c.execute("""INSERT INTO email_sequence_steps (sequence_id, step_order, delay_days, 
                     delay_hours, template_id, subject, content_json)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (sequence_id, i + 1, step.get('delay_days', 0), step.get('delay_hours', 0),
                   step.get('template_id'), step.get('subject'), step.get('content_json')))
    
    conn.commit()
    conn.close()
    return sequence_id


def start_sequence_for_client(sequence_id, client_id):
    """Démarre une séquence pour un client."""
    conn = get_connection()
    c = conn.cursor()
    
    # Vérifier si pas déjà en cours
    existing = c.execute("""SELECT id FROM email_sequence_history 
                            WHERE sequence_id=? AND client_id=? AND status='en_cours'""",
                         (sequence_id, client_id)).fetchone()
    if existing: 
        conn.close()
        return None
    
    # Calculer la prochaine date d'envoi
    sequence, steps = get_sequence_with_steps(sequence_id)
    if not steps:
        conn.close()
        return None
    
    first_step = steps[0]
    delay = timedelta(days=first_step['delay_days'], hours=first_step['delay_hours'])
    next_send = (datetime.now() + delay).isoformat()
    
    c.execute("""INSERT INTO email_sequence_history (sequence_id, client_id, current_step, next_send_at)
                 VALUES (?, ?, 1, ?)""", (sequence_id, client_id, next_send))
    history_id = c.lastrowid
    
    conn.commit()
    conn.close()
    return history_id


# ============================================================================
# FONCTIONS IMPORT/EXPORT
# ============================================================================
def export_clients_csv(filepath):
    """Exporte les clients en CSV."""
    conn = get_connection()
    clients = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    
    if not clients: return False, "Aucun client à exporter"
    
    fieldnames = clients[0].keys()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for client in clients:
            writer.writerow(dict(client))
    
    return True, f"{len(clients)} clients exportés"


def import_clients_csv(filepath):
    """Importe des clients depuis un CSV."""
    imported = 0
    errors = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Mapper les colonnes possibles
                    name = row.get('name') or row.get('nom') or row.get('Nom') or row.get('raison_sociale')
                    if not name:
                        errors.append(f"Ligne sans nom: {row}")
                        continue
                    
                    data = {
                        'name': name,
                        'email': row.get('email') or row.get('Email') or row.get('mail'),
                        'phone': row.get('phone') or row.get('telephone') or row.get('Téléphone') or row.get('tel'),
                        'address': row.get('address') or row.get('adresse') or row.get('Adresse'),
                        'client_type': row.get('client_type') or row.get('type') or 'particulier',
                        'newsletter': 1 if row.get('newsletter', '1').lower() in ['1', 'oui', 'yes', 'true'] else 0,
                        'is_prospect': 1 if row.get('is_prospect', '0').lower() in ['1', 'oui', 'yes', 'true'] else 0,
                        'notes': row.get('notes') or row.get('Notes'),
                        'ridet': row.get('ridet') or row.get('RIDET'),
                    }
                    
                    save_client(data)
                    imported += 1
                except Exception as e:
                    errors.append(f"Erreur ligne {imported + 1}: {str(e)}")
        
        return True, f"{imported} clients importés" + (f", {len(errors)} erreurs" if errors else "")
    except Exception as e:
        return False, f"Erreur: {str(e)}"


def export_products_csv(filepath):
    """Exporte les produits en CSV."""
    conn = get_connection()
    products = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
    conn.close()
    
    if not products: return False, "Aucun produit à exporter"
    
    fieldnames = products[0].keys()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for product in products:
            writer.writerow(dict(product))
    
    return True, f"{len(products)} produits exportés"


def backup_database(backup_path=None):
    """Crée une sauvegarde de la base de données."""
    if not backup_path:
        backup_path = f"krysto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        return True, f"Sauvegarde créée: {backup_path}"
    except Exception as e:
        return False, f"Erreur: {str(e)}"


def restore_database(backup_path):
    """Restaure la base de données depuis une sauvegarde."""
    try:
        # Vérifier que c'est une base SQLite valide
        test_conn = sqlite3.connect(backup_path)
        test_conn.execute("SELECT * FROM clients LIMIT 1")
        test_conn.close()
        
        # Créer une sauvegarde de l'actuelle avant restauration
        backup_database(f"krysto_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        
        # Restaurer
        shutil.copy2(backup_path, DB_PATH)
        return True, "Base de données restaurée"
    except Exception as e:
        return False, f"Erreur: {str(e)}"


# ============================================================================
# FONCTIONS STATISTIQUES
# ============================================================================
def get_dashboard_stats():
    """Récupère les statistiques pour le dashboard."""
    conn = get_connection()
    c = conn.cursor()
    
    stats = {}
    
    # Clients
    stats['total_clients'] = c.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    stats['total_prospects'] = c.execute("SELECT COUNT(*) FROM clients WHERE is_prospect=1").fetchone()[0]
    stats['total_newsletter'] = c.execute("SELECT COUNT(*) FROM clients WHERE newsletter=1").fetchone()[0]
    stats['new_clients_month'] = c.execute("""SELECT COUNT(*) FROM clients 
        WHERE date_created >= date('now', '-30 days')""").fetchone()[0]
    
    # Produits
    stats['total_products'] = c.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]
    
    # Dettes
    debt = c.execute("""SELECT SUM(dette_m1 + dette_m2 + dette_m3 + dette_m3plus) 
                        FROM clients WHERE client_type='professionnel'""").fetchone()[0]
    stats['total_debt'] = debt or 0
    stats['clients_with_debt'] = c.execute("""SELECT COUNT(*) FROM clients 
        WHERE (dette_m1 > 0 OR dette_m2 > 0 OR dette_m3 > 0 OR dette_m3plus > 0)""").fetchone()[0]
    
    # Devis/Factures
    stats['quotes_pending'] = c.execute("SELECT COUNT(*) FROM quotes WHERE status='envoyé'").fetchone()[0]
    stats['quotes_month'] = c.execute("""SELECT COUNT(*) FROM quotes 
        WHERE date_created >= date('now', '-30 days')""").fetchone()[0]
    stats['invoices_unpaid'] = c.execute("""SELECT COUNT(*) FROM invoices 
        WHERE status IN ('envoyée', 'en_retard')""").fetchone()[0]
    
    revenue = c.execute("SELECT SUM(total) FROM invoices WHERE status='payée'").fetchone()[0]
    stats['total_revenue'] = revenue or 0
    
    revenue_month = c.execute("""SELECT SUM(total) FROM invoices 
        WHERE status='payée' AND date_paid >= date('now', '-30 days')""").fetchone()[0]
    stats['revenue_month'] = revenue_month or 0
    
    # Tâches
    stats['tasks_pending'] = c.execute("SELECT COUNT(*) FROM tasks WHERE status='à faire'").fetchone()[0]
    stats['tasks_overdue'] = c.execute("""SELECT COUNT(*) FROM tasks 
        WHERE status='à faire' AND due_date < date('now')""").fetchone()[0]
    
    # Conversion prospects
    total_converted = c.execute("""SELECT COUNT(*) FROM clients 
        WHERE is_prospect=0 AND date_created >= date('now', '-90 days')""").fetchone()[0]
    if stats['total_prospects'] + total_converted > 0:
        stats['conversion_rate'] = round(total_converted / (stats['total_prospects'] + total_converted) * 100, 1)
    else:
        stats['conversion_rate'] = 0
    
    conn.close()
    return stats


def get_monthly_stats(months=12):
    """Récupère les statistiques mensuelles."""
    conn = get_connection()
    c = conn.cursor()
    
    stats = []
    for i in range(months - 1, -1, -1):
        month_start = (datetime.now().replace(day=1) - timedelta(days=i * 30)).strftime('%Y-%m-01')
        month_end = (datetime.now().replace(day=1) - timedelta(days=(i - 1) * 30)).strftime('%Y-%m-01')
        
        new_clients = c.execute("""SELECT COUNT(*) FROM clients 
            WHERE date_created >= ? AND date_created < ?""", (month_start, month_end)).fetchone()[0]
        
        revenue = c.execute("""SELECT SUM(total) FROM invoices 
            WHERE status='payée' AND date_paid >= ? AND date_paid < ?""", 
            (month_start, month_end)).fetchone()[0] or 0
        
        quotes = c.execute("""SELECT COUNT(*) FROM quotes 
            WHERE date_created >= ? AND date_created < ?""", (month_start, month_end)).fetchone()[0]
        
        stats.append({
            'month': month_start[:7],
            'new_clients': new_clients,
            'revenue': revenue,
            'quotes': quotes
        })
    
    conn.close()
    return stats


def get_top_clients(limit=10):
    """Récupère les meilleurs clients (par CA facturé)."""
    conn = get_connection()
    clients = conn.execute("""
        SELECT c.id, c.name, c.email, COUNT(i.id) as invoice_count, SUM(i.total) as total_revenue
        FROM clients c
        LEFT JOIN invoices i ON c.id = i.client_id AND i.status='payée'
        GROUP BY c.id
        ORDER BY total_revenue DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return clients


def get_conversion_funnel():
    """Récupère les données du funnel de conversion."""
    conn = get_connection()
    c = conn.cursor()
    
    funnel = {
        'prospects': c.execute("SELECT COUNT(*) FROM clients WHERE is_prospect=1").fetchone()[0],
        'clients': c.execute("SELECT COUNT(*) FROM clients WHERE is_prospect=0").fetchone()[0],
        'with_quotes': c.execute("SELECT COUNT(DISTINCT client_id) FROM quotes").fetchone()[0],
        'with_invoices': c.execute("SELECT COUNT(DISTINCT client_id) FROM invoices").fetchone()[0],
        'with_paid': c.execute("SELECT COUNT(DISTINCT client_id) FROM invoices WHERE status='payée'").fetchone()[0],
    }
    
    conn.close()
    return funnel


def toggle_client_block(client_id, block=True, motif=""):
    """Bloque ou débloque un client."""
    conn = get_connection()
    if block:
        conn.execute("UPDATE clients SET bloque=1, motif_blocage=?, date_blocage=? WHERE id=?",
                     (motif, datetime.now().isoformat(), client_id))
    else:
        conn.execute("UPDATE clients SET bloque=0, motif_blocage=NULL, date_blocage=NULL WHERE id=?",
                     (client_id,))
    conn.commit()
    conn.close()


def rotate_debts():
    """Fait tourner les dettes M1→M2→M3→M3+ après 30 jours. À appeler régulièrement."""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    rotations = 0
    
    # Récupérer tous les clients pro avec des dettes
    clients = c.execute("""SELECT id, dette_m1, dette_m2, dette_m3, dette_m3plus,
                           date_dette_m1, date_dette_m2, date_dette_m3 
                           FROM clients WHERE client_type='professionnel' 
                           AND (dette_m1 > 0 OR dette_m2 > 0 OR dette_m3 > 0)""").fetchall()
    
    for client in clients:
        client_id = client[0]
        m1, m2, m3, m3plus = client[1] or 0, client[2] or 0, client[3] or 0, client[4] or 0
        date_m1, date_m2, date_m3 = client[5], client[6], client[7]
        
        new_m1, new_m2, new_m3, new_m3plus = m1, m2, m3, m3plus
        new_date_m1, new_date_m2, new_date_m3 = date_m1, date_m2, date_m3
        changed = False
        
        # M3 → M3+ (après 30 jours)
        if m3 > 0 and date_m3:
            try:
                dt = datetime.fromisoformat(date_m3)
                if (now - dt).days >= 30:
                    new_m3plus += m3
                    new_m3 = 0
                    new_date_m3 = None
                    changed = True
            except: pass
        
        # M2 → M3 (après 30 jours)
        if m2 > 0 and date_m2:
            try:
                dt = datetime.fromisoformat(date_m2)
                if (now - dt).days >= 30:
                    new_m3 += m2
                    new_date_m3 = now.isoformat()
                    new_m2 = 0
                    new_date_m2 = None
                    changed = True
            except: pass
        
        # M1 → M2 (après 30 jours)
        if m1 > 0 and date_m1:
            try:
                dt = datetime.fromisoformat(date_m1)
                if (now - dt).days >= 30:
                    new_m2 += m1
                    new_date_m2 = now.isoformat()
                    new_m1 = 0
                    new_date_m1 = None
                    changed = True
            except: pass
        
        if changed:
            c.execute("""UPDATE clients SET dette_m1=?, dette_m2=?, dette_m3=?, dette_m3plus=?,
                         date_dette_m1=?, date_dette_m2=?, date_dette_m3=? WHERE id=?""",
                      (new_m1, new_m2, new_m3, new_m3plus, new_date_m1, new_date_m2, new_date_m3, client_id))
            rotations += 1
    
    conn.commit()
    conn.close()
    return rotations


def get_clients_with_debt():
    """Retourne les clients pro avec des impayés."""
    conn = get_connection()
    clients = conn.execute("""SELECT * FROM clients WHERE client_type='professionnel'
                              AND (dette_m1 > 0 OR dette_m2 > 0 OR dette_m3 > 0 OR dette_m3plus > 0)
                              ORDER BY (COALESCE(dette_m1,0) + COALESCE(dette_m2,0) + 
                                        COALESCE(dette_m3,0) + COALESCE(dette_m3plus,0)) DESC""").fetchall()
    conn.close()
    return clients


def send_monthly_debt_reminders():
    """Envoie les rappels mensuels d'impayés. À appeler le 1er du mois."""
    clients = get_clients_with_debt()
    if not clients:
        return {"sent": 0, "errors": []}
    
    # Template de rappel
    template = get_debt_reminder_template()
    service = EmailService()
    results = {"sent": 0, "errors": []}
    
    for client in clients:
        email = client['email'] if 'email' in client.keys() else None
        if not email:
            continue
        
        name = client['name'] if 'name' in client.keys() else ''
        m1 = client['dette_m1'] if 'dette_m1' in client.keys() else 0
        m2 = client['dette_m2'] if 'dette_m2' in client.keys() else 0
        m3 = client['dette_m3'] if 'dette_m3' in client.keys() else 0
        m3plus = client['dette_m3plus'] if 'dette_m3plus' in client.keys() else 0
        total = (m1 or 0) + (m2 or 0) + (m3 or 0) + (m3plus or 0)
        bloque = client['bloque'] if 'bloque' in client.keys() else 0
        
        # Personnaliser le template
        html = template.replace("{{name}}", name)
        html = html.replace("{{dette_m1}}", format_price(m1 or 0))
        html = html.replace("{{dette_m2}}", format_price(m2 or 0))
        html = html.replace("{{dette_m3}}", format_price(m3 or 0))
        html = html.replace("{{dette_m3plus}}", format_price(m3plus or 0))
        html = html.replace("{{dette_total}}", format_price(total))
        html = html.replace("{{date}}", datetime.now().strftime("%d/%m/%Y"))
        
        # Message de blocage si applicable
        if bloque:
            blocage_msg = '<div style="background:#dc3545;color:white;padding:15px;border-radius:8px;margin:20px 0;text-align:center;"><strong>⚠️ COMPTE BLOQUÉ</strong><br>Aucune nouvelle vente ne sera effectuée tant que le solde ne sera pas régularisé.</div>'
            html = html.replace("{{blocage_message}}", blocage_msg)
        else:
            html = html.replace("{{blocage_message}}", "")
        
        subject = f"[KRYSTO] Rappel impayés - {format_price(total)} en attente"
        success, msg = service.send_email(email, subject, html, name)
        
        if success:
            results["sent"] += 1
            update_client_rappel(client['id'])
        else:
            results["errors"].append({"email": email, "error": msg})
        
        import time
        time.sleep(0.5)
    
    return results


def get_debt_reminder_template():
    """Retourne le template HTML pour les rappels d'impayés."""
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:Segoe UI,sans-serif;background:#f4f4f4;margin:0;padding:20px;">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
<div style="background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});padding:30px;text-align:center;">
<h1 style="margin:0;color:white;font-size:24px;">{COMPANY_NAME}</h1>
<p style="margin:10px 0 0;color:rgba(255,255,255,0.9);">Rappel de paiement</p>
</div>
<div style="padding:30px;">
<p style="font-size:16px;color:#333;">Bonjour <strong>{{{{name}}}}</strong>,</p>
<p style="color:#666;line-height:1.6;">Nous vous informons que votre compte présente un solde impayé. Voici le détail de vos encours :</p>

<div style="background:#f8f9fa;border-radius:10px;padding:20px;margin:20px 0;">
<table style="width:100%;border-collapse:collapse;">
<tr><td style="padding:8px 0;color:#666;">Encours M1 (0-30j)</td><td style="text-align:right;font-weight:bold;color:{KRYSTO_PRIMARY};">{{{{dette_m1}}}}</td></tr>
<tr><td style="padding:8px 0;color:#666;">Encours M2 (30-60j)</td><td style="text-align:right;font-weight:bold;color:#ff9800;">{{{{dette_m2}}}}</td></tr>
<tr><td style="padding:8px 0;color:#666;">Encours M3 (60-90j)</td><td style="text-align:right;font-weight:bold;color:#f44336;">{{{{dette_m3}}}}</td></tr>
<tr><td style="padding:8px 0;color:#666;">Encours M3+ (>90j)</td><td style="text-align:right;font-weight:bold;color:#d32f2f;">{{{{dette_m3plus}}}}</td></tr>
<tr style="border-top:2px solid #ddd;"><td style="padding:12px 0;font-weight:bold;font-size:18px;">TOTAL DÛ</td><td style="text-align:right;font-weight:bold;font-size:18px;color:#dc3545;">{{{{dette_total}}}}</td></tr>
</table>
</div>

{{{{blocage_message}}}}

<p style="color:#666;line-height:1.6;">Nous vous remercions de bien vouloir régulariser votre situation dans les meilleurs délais.</p>
<p style="color:#666;">Pour toute question, n'hésitez pas à nous contacter.</p>

<p style="margin-top:30px;color:#333;">Cordialement,<br><strong>L'équipe {COMPANY_NAME}</strong></p>
</div>
<div style="background:{KRYSTO_DARK};padding:20px;text-align:center;">
<p style="margin:0;color:rgba(255,255,255,0.7);font-size:12px;">{COMPANY_ADDRESS} | {COMPANY_EMAIL}</p>
</div>
</div>
</body></html>'''

def delete_client(client_id):
    conn = get_connection()
    conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()

def update_client_rappel(client_id):
    conn = get_connection()
    conn.execute("UPDATE clients SET dernier_rappel=? WHERE id=?", (datetime.now().isoformat(), client_id))
    conn.commit()
    conn.close()

# Produits
def get_all_products(active_only=True):
    conn = get_connection()
    query = "SELECT * FROM products"
    if active_only: query += " WHERE active=1"
    query += " ORDER BY name"
    products = conn.execute(query).fetchall()
    conn.close()
    return products

def get_product(product_id):
    conn = get_connection()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return product

def save_product(data, product_id=None):
    conn = get_connection()
    c = conn.cursor()
    if product_id:
        c.execute("""UPDATE products SET name=?, description=?, category=?, price=?, cost=?, 
                     stock=?, image_url=?, image_url_2=?, image_url_3=?, active=?,
                     prix_particulier=?, prix_pro=? WHERE id=?""",
                  (data['name'], data.get('description'), data.get('category'), data.get('price', 0),
                   data.get('cost', 0), data.get('stock', 0), data.get('image_url'), 
                   data.get('image_url_2'), data.get('image_url_3'), data.get('active', 1),
                   data.get('prix_particulier', data.get('price', 0)),
                   data.get('prix_pro', data.get('price', 0)), product_id))
    else:
        c.execute("""INSERT INTO products (name, description, category, price, cost, stock, 
                     image_url, image_url_2, image_url_3, active, prix_particulier, prix_pro)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (data['name'], data.get('description'), data.get('category'), data.get('price', 0),
                   data.get('cost', 0), data.get('stock', 0), data.get('image_url'),
                   data.get('image_url_2'), data.get('image_url_3'), data.get('active', 1),
                   data.get('prix_particulier', data.get('price', 0)),
                   data.get('prix_pro', data.get('price', 0))))
        product_id = c.lastrowid
    conn.commit()
    conn.close()
    return product_id

def delete_product(product_id):
    conn = get_connection()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

# Dépôts
def get_all_depots(active_only=True):
    conn = get_connection()
    query = """SELECT d.*, c.name as client_name, c.email as client_email, c.phone as client_phone, 
               c.address as client_address, c.ridet as client_ridet, c.forme_juridique as client_forme
               FROM depots d JOIN clients c ON d.client_id = c.id"""
    if active_only: query += " WHERE d.active=1"
    query += " ORDER BY c.name"
    depots = conn.execute(query).fetchall()
    conn.close()
    return depots

def get_depot(depot_id):
    conn = get_connection()
    depot = conn.execute("""SELECT d.*, c.name as client_name, c.email as client_email, c.phone as client_phone, 
                            c.address as client_address, c.ridet as client_ridet, c.forme_juridique as client_forme
                            FROM depots d JOIN clients c ON d.client_id = c.id WHERE d.id=?""", (depot_id,)).fetchone()
    conn.close()
    return depot

def save_depot(data, depot_id=None):
    conn = get_connection()
    c = conn.cursor()
    if depot_id:
        c.execute("""UPDATE depots SET client_id=?, commission_percent=?, notes=?, active=? WHERE id=?""",
                  (data['client_id'], data.get('commission_percent', 0), data.get('notes'), data.get('active', 1), depot_id))
    else:
        c.execute("""INSERT INTO depots (client_id, commission_percent, notes, active) VALUES (?,?,?,?)""",
                  (data['client_id'], data.get('commission_percent', 0), data.get('notes'), data.get('active', 1)))
        depot_id = c.lastrowid
    conn.commit()
    conn.close()
    return depot_id

def get_clients_without_depot():
    """Retourne les clients pro qui n'ont pas encore de dépôt."""
    conn = get_connection()
    clients = conn.execute("""SELECT * FROM clients WHERE client_type='professionnel' 
                              AND id NOT IN (SELECT client_id FROM depots WHERE active=1)
                              ORDER BY name""").fetchall()
    conn.close()
    return clients

def get_pro_clients():
    """Retourne tous les clients pro."""
    conn = get_connection()
    clients = conn.execute("SELECT * FROM clients WHERE client_type='professionnel' ORDER BY name").fetchall()
    conn.close()
    return clients


# Paramètres globaux (catalogue, etc.)
def get_setting(key, default=None):
    """Récupère un paramètre."""
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    """Enregistre un paramètre."""
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_catalog_url():
    """Retourne l'URL du catalogue téléchargeable."""
    return get_setting('catalog_url', '')

def set_catalog_url(url):
    """Enregistre l'URL du catalogue."""
    set_setting('catalog_url', url)

def delete_depot(depot_id):
    conn = get_connection()
    conn.execute("DELETE FROM depot_products WHERE depot_id=?", (depot_id,))
    conn.execute("DELETE FROM depot_history WHERE depot_id=?", (depot_id,))
    conn.execute("DELETE FROM depots WHERE id=?", (depot_id,))
    conn.commit()
    conn.close()

# Produits en dépôt
def get_depot_products(depot_id):
    conn = get_connection()
    products = conn.execute("""SELECT dp.*, p.name as product_name, p.price as product_price
                               FROM depot_products dp JOIN products p ON dp.product_id = p.id
                               WHERE dp.depot_id=? ORDER BY p.name""", (depot_id,)).fetchall()
    conn.close()
    return products

def get_depot_product(depot_id, product_id):
    conn = get_connection()
    dp = conn.execute("SELECT * FROM depot_products WHERE depot_id=? AND product_id=?", 
                      (depot_id, product_id)).fetchone()
    conn.close()
    return dp

def add_depot_product(depot_id, product_id, quantity, price=None, discount=0):
    conn = get_connection()
    c = conn.cursor()
    existing = c.execute("SELECT id, quantity_deposited FROM depot_products WHERE depot_id=? AND product_id=?",
                         (depot_id, product_id)).fetchone()
    if existing:
        c.execute("UPDATE depot_products SET quantity_deposited=quantity_deposited+?, last_update=?, discount_percent=? WHERE id=?",
                  (quantity, datetime.now().isoformat(), discount, existing[0]))
    else:
        c.execute("""INSERT INTO depot_products (depot_id, product_id, quantity_deposited, price_depot, discount_percent)
                     VALUES (?,?,?,?,?)""", (depot_id, product_id, quantity, price, discount))
    c.execute("""INSERT INTO depot_history (depot_id, product_id, action, quantity, date_action)
                 VALUES (?,?,?,?,?)""", (depot_id, product_id, 'depot', quantity, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def record_depot_sale(depot_id, product_id, quantity, amount=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""UPDATE depot_products SET quantity_sold=quantity_sold+?, last_update=? 
                 WHERE depot_id=? AND product_id=?""",
              (quantity, datetime.now().isoformat(), depot_id, product_id))
    c.execute("""INSERT INTO depot_history (depot_id, product_id, action, quantity, amount, date_action)
                 VALUES (?,?,?,?,?,?)""", (depot_id, product_id, 'vente', quantity, amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def record_depot_return(depot_id, product_id, quantity):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""UPDATE depot_products SET quantity_returned=quantity_returned+?, last_update=? 
                 WHERE depot_id=? AND product_id=?""",
              (quantity, datetime.now().isoformat(), depot_id, product_id))
    c.execute("""INSERT INTO depot_history (depot_id, product_id, action, quantity, date_action)
                 VALUES (?,?,?,?,?)""", (depot_id, product_id, 'retour', quantity, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_depot_stats(depot_id):
    conn = get_connection()
    stats = conn.execute("""SELECT 
        SUM(quantity_deposited) as total_deposited,
        SUM(quantity_sold) as total_sold,
        SUM(quantity_returned) as total_returned,
        SUM(quantity_deposited - quantity_sold - quantity_returned) as in_stock,
        SUM(quantity_invoiced) as total_invoiced
        FROM depot_products WHERE depot_id=?""", (depot_id,)).fetchone()
    conn.close()
    return dict(stats) if stats else {}


def get_depot_sales_to_invoice(depot_id):
    """Récupère les ventes du dépôt non encore facturées."""
    conn = get_connection()
    products = conn.execute("""
        SELECT dp.*, p.name as product_name, p.prix_particulier, p.prix_pro
        FROM depot_products dp
        JOIN products p ON dp.product_id = p.id
        WHERE dp.depot_id = ? AND dp.quantity_sold > dp.quantity_invoiced
    """, (depot_id,)).fetchall()
    conn.close()
    return [dict(p) for p in products]


def create_depot_invoice(depot_id):
    """Crée une facture pour les ventes du dépôt non facturées et enregistre dans caisse_sales."""
    # Récupérer le dépôt et le client
    depot = get_depot(depot_id)
    if not depot:
        return None, "Dépôt non trouvé"
    
    depot = dict(depot)
    client_id = depot['client_id']
    
    # Récupérer les ventes non facturées
    products_to_invoice = get_depot_sales_to_invoice(depot_id)
    
    if not products_to_invoice:
        return None, "Aucune vente à facturer"
    
    # Créer les lignes de facture
    lines = []
    for p in products_to_invoice:
        qty_to_invoice = p['quantity_sold'] - (p.get('quantity_invoiced') or 0)
        if qty_to_invoice > 0:
            # Utiliser le prix dépôt si défini, sinon prix_pro
            unit_price = p.get('price_depot') or p.get('prix_pro') or p.get('prix_particulier') or 0
            discount = p.get('discount_percent') or 0
            total = unit_price * qty_to_invoice * (1 - discount / 100)
            
            lines.append({
                'product_id': p['product_id'],
                'description': f"Dépôt-vente: {p['product_name']}",
                'quantity': qty_to_invoice,
                'unit_price': unit_price,
                'discount_percent': discount,
                'total': total
            })
    
    if not lines:
        return None, "Aucune ligne à facturer"
    
    # Calculer les totaux
    subtotal = sum(l['total'] for l in lines)
    tgc_percent = TGC_RATES.get(DEFAULT_TGC_RATE, 11)
    tgc_amount = subtotal * tgc_percent / 100
    total = subtotal + tgc_amount
    
    # Créer la facture
    invoice_data = {
        'client_id': client_id,
        'tgc_rate': DEFAULT_TGC_RATE,
        'status': 'payée',
        'amount_paid': total,
        'date_paid': datetime.now().strftime('%Y-%m-%d'),
        'notes': f"Ventes dépôt-vente #{depot_id}"
    }
    
    invoice_id = save_invoice(invoice_data, lines)
    
    # Enregistrer dans caisse_sales pour le CA et le ticket Z
    sale_data = {
        'client_id': client_id,
        'subtotal': subtotal,
        'tgc_amount': tgc_amount,
        'total': total,
        'payment_method': 'autre',
        'notes': f"Dépôt-vente #{depot_id}"
    }
    save_caisse_sale(sale_data, invoice_id)
    
    # Mettre à jour les quantités facturées
    conn = get_connection()
    for p in products_to_invoice:
        qty_to_invoice = p['quantity_sold'] - (p.get('quantity_invoiced') or 0)
        conn.execute("""UPDATE depot_products SET quantity_invoiced = quantity_invoiced + ? 
                       WHERE depot_id = ? AND product_id = ?""",
                    (qty_to_invoice, depot_id, p['product_id']))
    conn.commit()
    conn.close()
    
    return invoice_id, {'total': total, 'nb_products': len(lines), 'subtotal': subtotal}


# Groupes de clients
def get_all_client_groups():
    conn = get_connection()
    groups = conn.execute("SELECT * FROM client_groups ORDER BY name").fetchall()
    conn.close()
    return groups

def get_client_group(group_id):
    conn = get_connection()
    group = conn.execute("SELECT * FROM client_groups WHERE id=?", (group_id,)).fetchone()
    conn.close()
    return group

def save_client_group(name, description="", color="#6d74ab", group_id=None):
    conn = get_connection()
    c = conn.cursor()
    if group_id:
        c.execute("UPDATE client_groups SET name=?, description=?, color=? WHERE id=?",
                  (name, description, color, group_id))
    else:
        c.execute("INSERT INTO client_groups (name, description, color) VALUES (?,?,?)",
                  (name, description, color))
        group_id = c.lastrowid
    conn.commit()
    conn.close()
    return group_id

def delete_client_group(group_id):
    conn = get_connection()
    conn.execute("DELETE FROM client_group_members WHERE group_id=?", (group_id,))
    conn.execute("DELETE FROM client_groups WHERE id=?", (group_id,))
    conn.commit()
    conn.close()

def get_group_members(group_id):
    conn = get_connection()
    members = conn.execute("""SELECT c.* FROM clients c
        INNER JOIN client_group_members m ON c.id = m.client_id
        WHERE m.group_id=? ORDER BY c.name""", (group_id,)).fetchall()
    conn.close()
    return members

def get_group_member_count(group_id):
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM client_group_members WHERE group_id=?", (group_id,)).fetchone()[0]
    conn.close()
    return count

def add_client_to_group(client_id, group_id):
    conn = get_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO client_group_members (client_id, group_id) VALUES (?,?)",
                     (client_id, group_id))
        conn.commit()
    except: pass
    conn.close()

def remove_client_from_group(client_id, group_id):
    conn = get_connection()
    conn.execute("DELETE FROM client_group_members WHERE client_id=? AND group_id=?",
                 (client_id, group_id))
    conn.commit()
    conn.close()

def get_client_groups_for_client(client_id):
    conn = get_connection()
    groups = conn.execute("""SELECT g.* FROM client_groups g
        INNER JOIN client_group_members m ON g.id = m.group_id
        WHERE m.client_id=? ORDER BY g.name""", (client_id,)).fetchall()
    conn.close()
    return groups

def add_multiple_clients_to_group(client_ids, group_id):
    conn = get_connection()
    for client_id in client_ids:
        try:
            conn.execute("INSERT OR IGNORE INTO client_group_members (client_id, group_id) VALUES (?,?)",
                         (client_id, group_id))
        except: pass
    conn.commit()
    conn.close()

# Templates email
def save_email_template(name, subject, design_json, template_type='marketing', template_id=None):
    conn = get_connection()
    c = conn.cursor()
    if template_id:
        c.execute("UPDATE email_templates SET name=?, subject=?, design_json=?, template_type=?, date_modified=? WHERE id=?",
                  (name, subject, design_json, template_type, datetime.now().isoformat(), template_id))
    else:
        c.execute("INSERT INTO email_templates (name, subject, design_json, template_type) VALUES (?,?,?,?)",
                  (name, subject, design_json, template_type))
        template_id = c.lastrowid
    conn.commit()
    conn.close()
    return template_id

def get_email_templates(template_type=None):
    conn = get_connection()
    if template_type:
        templates = conn.execute("SELECT * FROM email_templates WHERE template_type=? ORDER BY date_modified DESC",
                                 (template_type,)).fetchall()
    else:
        templates = conn.execute("SELECT * FROM email_templates ORDER BY date_modified DESC").fetchall()
    conn.close()
    return templates

def get_email_template(template_id):
    conn = get_connection()
    template = conn.execute("SELECT * FROM email_templates WHERE id=?", (template_id,)).fetchone()
    conn.close()
    return template

def delete_email_template(template_id):
    conn = get_connection()
    conn.execute("DELETE FROM email_templates WHERE id=?", (template_id,))
    conn.commit()
    conn.close()


# Templates pour dépôts-ventes
def get_depot_restock_template():
    """Template pour demander si besoin de réapprovisionnement."""
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:Segoe UI,sans-serif;background:#f4f4f4;margin:0;padding:20px;">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
<div style="background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});padding:30px;text-align:center;">
<h1 style="margin:0;color:white;font-size:24px;">{COMPANY_NAME}</h1>
<p style="margin:10px 0 0;color:rgba(255,255,255,0.9);">Suivi Dépôt-Vente</p>
</div>
<div style="padding:30px;">
<p style="font-size:16px;color:#333;">Bonjour <strong>{{{{name}}}}</strong>,</p>
<p style="color:#666;line-height:1.6;">Nous espérons que nos produits se vendent bien dans votre établissement !</p>

<div style="background:#e8f5e9;border-left:4px solid {KRYSTO_SECONDARY};padding:15px;margin:20px 0;border-radius:0 8px 8px 0;">
<p style="margin:0;color:#2e7d32;font-weight:bold;">📦 État actuel de votre stock</p>
<p style="margin:10px 0 0;color:#666;">Produits en dépôt: <strong>{{{{stock_count}}}}</strong> articles</p>
<p style="margin:5px 0 0;color:#666;">Vendus ce mois: <strong>{{{{sold_count}}}}</strong> articles</p>
</div>

<p style="color:#666;line-height:1.6;"><strong>Avez-vous besoin de réapprovisionnement ?</strong></p>
<p style="color:#666;line-height:1.6;">N'hésitez pas à nous contacter pour :</p>
<ul style="color:#666;">
<li>Réapprovisionner les produits qui se vendent bien</li>
<li>Échanger les articles qui ont moins de succès</li>
<li>Découvrir nos nouveautés</li>
</ul>

<div style="text-align:center;margin:25px 0;">
<a href="mailto:{COMPANY_EMAIL}?subject=Réapprovisionnement%20dépôt-vente" style="display:inline-block;padding:14px 40px;background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});color:white;text-decoration:none;border-radius:25px;font-weight:bold;">📧 Nous contacter</a>
</div>

<p style="color:#333;">Cordialement,<br><strong>L'équipe {COMPANY_NAME}</strong></p>
</div>
<div style="background:{KRYSTO_DARK};padding:20px;text-align:center;">
<p style="margin:0;color:rgba(255,255,255,0.7);font-size:12px;">{COMPANY_ADDRESS} | {COMPANY_EMAIL}</p>
</div>
</div>
</body></html>'''


def get_depot_new_products_template():
    """Template pour proposer de nouveaux produits avec images."""
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:Segoe UI,sans-serif;background:#f4f4f4;margin:0;padding:20px;">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
<div style="background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});padding:30px;text-align:center;">
<h1 style="margin:0;color:white;font-size:24px;">🎉 Nouveautés {COMPANY_NAME}</h1>
<p style="margin:10px 0 0;color:rgba(255,255,255,0.9);">De nouveaux produits pour votre boutique !</p>
</div>
<div style="padding:30px;">
<p style="font-size:16px;color:#333;">Bonjour <strong>{{{{name}}}}</strong>,</p>
<p style="color:#666;line-height:1.6;">Nous avons le plaisir de vous présenter nos <strong>nouveaux produits</strong> disponibles en dépôt-vente :</p>

{{{{products_list}}}}

<div style="background:linear-gradient(135deg,{KRYSTO_PRIMARY}22,{KRYSTO_SECONDARY}22);padding:20px;border-radius:10px;margin:20px 0;text-align:center;">
<p style="margin:0;font-size:18px;color:{KRYSTO_PRIMARY};font-weight:bold;">💡 Conditions habituelles</p>
<p style="margin:10px 0 0;color:#666;">Commission: <strong>{{{{commission}}}}%</strong> sur les ventes</p>
<p style="margin:5px 0 0;color:#666;">Retour des invendus possible à tout moment</p>
</div>

{{{{catalog_section}}}}

<p style="color:#666;line-height:1.6;">Intéressé(e) ? Répondez simplement à cet email avec les références souhaitées et les quantités.</p>

<div style="text-align:center;margin:25px 0;">
<a href="mailto:{COMPANY_EMAIL}?subject=Commande%20nouveaux%20produits" style="display:inline-block;padding:14px 40px;background:linear-gradient(135deg,{KRYSTO_PRIMARY},{KRYSTO_SECONDARY});color:white;text-decoration:none;border-radius:25px;font-weight:bold;">🛒 Commander</a>
</div>

<p style="color:#333;">Cordialement,<br><strong>L'équipe {COMPANY_NAME}</strong></p>
</div>
<div style="background:{KRYSTO_DARK};padding:20px;text-align:center;">
<p style="margin:0;color:rgba(255,255,255,0.7);font-size:12px;">{COMPANY_ADDRESS} | {COMPANY_EMAIL}</p>
</div>
</div>
</body></html>'''


def send_depot_email(depot_id, email_type="restock", custom_products=None):
    """Envoie un email à un dépôt-vente."""
    depot = get_depot(depot_id)
    if not depot:
        return False, "Dépôt introuvable"
    
    email = depot['client_email'] if 'client_email' in depot.keys() else None
    if not email:
        return False, "Pas d'email pour ce dépôt"
    
    name = depot['client_name'] if 'client_name' in depot.keys() else ''
    commission = depot['commission_percent'] if 'commission_percent' in depot.keys() else 0
    
    # Stats du dépôt
    stats = get_depot_stats(depot_id)
    stock_count = int(stats.get('in_stock') or 0)
    sold_count = int(stats.get('total_sold') or 0)
    
    if email_type == "restock":
        template = get_depot_restock_template()
        subject = f"[{COMPANY_NAME}] Besoin de réapprovisionnement ?"
        html = template.replace("{{name}}", name)
        html = html.replace("{{stock_count}}", str(stock_count))
        html = html.replace("{{sold_count}}", str(sold_count))
    else:  # new_products
        template = get_depot_new_products_template()
        subject = f"[{COMPANY_NAME}] 🎉 Découvrez nos nouveautés !"
        html = template.replace("{{name}}", name)
        html = html.replace("{{commission}}", str(commission))
        
        # Liste des produits AVEC IMAGES
        if custom_products:
            products_html = '<div style="margin:20px 0;">'
            for p in custom_products:
                img_url = p.get('image_url', '')
                img_html = ""
                if img_url:
                    img_html = f'<img src="{img_url}" style="width:120px;height:120px;object-fit:cover;border-radius:10px;margin-right:15px;">'
                
                products_html += f'''<div style="background:#f8f9fa;padding:15px;border-radius:12px;margin:15px 0;display:flex;align-items:center;">
                {img_html}
                <div style="flex:1;">
                    <strong style="color:{KRYSTO_PRIMARY};font-size:16px;">{p['name']}</strong>
                    <p style="margin:8px 0;color:#666;font-size:14px;line-height:1.4;">{p.get('description', '')[:150]}{'...' if len(p.get('description', '')) > 150 else ''}</p>
                    <span style="font-size:18px;font-weight:bold;color:{KRYSTO_SECONDARY};">{format_price(p.get('price', 0))}</span>
                </div>
                </div>'''
            products_html += '</div>'
        else:
            products_html = '<p style="color:#888;font-style:italic;">Contactez-nous pour découvrir notre catalogue.</p>'
        
        html = html.replace("{{products_list}}", products_html)
        
        # Section catalogue si URL définie
        catalog_url = get_catalog_url()
        if catalog_url:
            catalog_section = f'''<div style="text-align:center;margin:25px 0;padding:20px;background:#f0f8ff;border-radius:10px;">
                <p style="margin:0 0 15px 0;color:{KRYSTO_DARK};font-size:15px;">📚 Consultez notre catalogue complet</p>
                <a href="{catalog_url}" style="display:inline-block;padding:12px 30px;background:{KRYSTO_DARK};color:white;text-decoration:none;border-radius:20px;font-weight:bold;">📥 Télécharger le catalogue</a>
            </div>'''
        else:
            catalog_section = ""
        
        html = html.replace("{{catalog_section}}", catalog_section)
    
    service = EmailService()
    return service.send_email(email, subject, html, name)


# ============================================================================
# SERVICE EMAIL
# ============================================================================
class EmailService:
    def __init__(self, config=None):
        self.config = config or load_smtp_config()
    
    def test_connection(self):
        try:
            if self.config['use_ssl']:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.config['host'], self.config['port'], context=context, timeout=10) as server:
                    server.login(self.config['username'], self.config['password'])
            else:
                with smtplib.SMTP(self.config['host'], self.config['port'], timeout=10) as server:
                    server.starttls()
                    server.login(self.config['username'], self.config['password'])
            return True, "Connexion réussie!"
        except Exception as e:
            return False, str(e)
    
    def _create_plain_text(self, html_content):
        """Convertit le HTML en texte brut pour la version alternative."""
        import re
        # Supprimer les styles et scripts
        text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        # Remplacer les balises de bloc par des retours à la ligne
        text = re.sub(r'</?(div|p|br|h[1-6]|tr|li)[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</?(td|th)[^>]*>', ' | ', text, flags=re.IGNORECASE)
        # Extraire le texte des liens
        text = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>([^<]*)</a>', r'\2 (\1)', text)
        # Supprimer toutes les autres balises HTML
        text = re.sub(r'<[^>]+>', '', text)
        # Nettoyer les espaces et retours à la ligne multiples
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        # Décoder les entités HTML
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text.strip()
    
    def send_email(self, to_email, subject, html_content, to_name=""):
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.config['from_name']} <{self.config['username']}>"
            msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
            
            # Headers anti-spam importants
            msg['Reply-To'] = self.config['username']
            msg['X-Mailer'] = f"{COMPANY_NAME} Mailer"
            msg['List-Unsubscribe'] = f"<mailto:{COMPANY_EMAIL}?subject=Désabonnement>"
            msg['Precedence'] = 'bulk'
            msg['X-Priority'] = '3'  # Normal priority
            msg['MIME-Version'] = '1.0'
            
            # Générer une version texte brut propre
            plain_text = self._create_plain_text(html_content)
            msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            if self.config['use_ssl']:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.config['host'], self.config['port'], context=context) as server:
                    server.login(self.config['username'], self.config['password'])
                    server.sendmail(self.config['username'], to_email, msg.as_string())
            else:
                with smtplib.SMTP(self.config['host'], self.config['port']) as server:
                    server.starttls()
                    server.login(self.config['username'], self.config['password'])
                    server.sendmail(self.config['username'], to_email, msg.as_string())
            return True, "Email envoyé"
        except Exception as e:
            return False, str(e)
    
    def send_bulk(self, recipients, subject, html_template, progress_callback=None):
        results = {"success": 0, "failed": 0, "errors": []}
        total = len(recipients)
        catalog_url = get_catalog_url() or ""
        
        for i, r in enumerate(recipients):
            # Remplacer toutes les variables
            html = html_template
            html = html.replace("{{name}}", r.get('name', ''))
            html = html.replace("{{email}}", r.get('email', ''))
            html = html.replace("{{date}}", datetime.now().strftime('%d/%m/%Y'))
            html = html.replace("{{catalog_url}}", catalog_url)
            html = html.replace("{{code_parrainage}}", r.get('code_parrainage', ''))
            html = html.replace("{{dette_m1}}", format_price(r.get('dette_m1', 0)))
            html = html.replace("{{dette_m2}}", format_price(r.get('dette_m2', 0)))
            html = html.replace("{{dette_m3}}", format_price(r.get('dette_m3', 0)))
            html = html.replace("{{dette_m3plus}}", format_price(r.get('dette_m3plus', 0)))
            html = html.replace("{{dette_total}}", format_price(
                r.get('dette_m1', 0) + r.get('dette_m2', 0) + r.get('dette_m3', 0) + r.get('dette_m3plus', 0)))
            
            # Remplacer PARRAIN-XXX par le vrai code
            html = html.replace("PARRAIN-XXX", f"PARRAIN-{r.get('code_parrainage', 'XXXX')}")
            
            success, message = self.send_email(r['email'], subject, html, r.get('name', ''))
            if success: 
                results["success"] += 1
            else: 
                results["failed"] += 1
                results["errors"].append({"email": r['email'], "error": message})
            
            if progress_callback: 
                progress_callback(i + 1, total, r['email'], success)
            
            # Délai entre les envois pour éviter d'être marqué comme spam
            import time
            time.sleep(0.8)
        
        return results


# ============================================================================
# DIALOGUES UI
# ============================================================================
class ColorPickerDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_color="#ffffff"):
        super().__init__(parent)
        self.title("Couleur")
        self.geometry("320x380")
        self.resizable(False, False)
        self.result = None
        self.initial_color = initial_color
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        ctk.CTkLabel(main, text="Couleurs KRYSTO", font=("Helvetica", 11, "bold")).pack(anchor="w")
        row1 = ctk.CTkFrame(main, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        for color in [KRYSTO_PRIMARY, KRYSTO_SECONDARY, KRYSTO_DARK, KRYSTO_LIGHT]:
            ctk.CTkButton(row1, text="", width=50, height=30, fg_color=color, hover_color=color,
                          command=lambda c=color: self._select(c)).pack(side="left", padx=2)
        
        ctk.CTkLabel(main, text="Courantes", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(10, 0))
        colors = ["#ffffff", "#000000", "#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff6b6b", "#4ecdc4", 
                  "#45b7d1", "#96ceb4", "#ffeaa7", "#dfe6e9", "#636e72", "#2d3436", "#fd79a8"]
        for i in range(0, len(colors), 5):
            row = ctk.CTkFrame(main, fg_color="transparent")
            row.pack(fill="x", pady=2)
            for color in colors[i:i+5]:
                ctk.CTkButton(row, text="", width=45, height=25, fg_color=color, hover_color=color,
                              command=lambda c=color: self._select(c)).pack(side="left", padx=2)
        
        ctk.CTkLabel(main, text="Code HEX:").pack(anchor="w", pady=(15, 5))
        row_hex = ctk.CTkFrame(main, fg_color="transparent")
        row_hex.pack(fill="x")
        self.hex_entry = ctk.CTkEntry(row_hex, width=100)
        self.hex_entry.pack(side="left")
        self.hex_entry.insert(0, self.initial_color)
        self.preview = ctk.CTkButton(row_hex, text="", width=40, height=30, fg_color=self.initial_color)
        self.preview.pack(side="left", padx=10)
        ctk.CTkButton(row_hex, text="🎨", width=40, command=self._system_picker).pack(side="left")
        
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="OK", fg_color=KRYSTO_PRIMARY, command=self._validate).pack(side="left", expand=True, padx=5)
    
    def _select(self, color):
        self.hex_entry.delete(0, "end")
        self.hex_entry.insert(0, color)
        self.preview.configure(fg_color=color)
    
    def _system_picker(self):
        color = colorchooser.askcolor(initialcolor=self.hex_entry.get())
        if color[1]: self._select(color[1])
    
    def _validate(self):
        self.result = self.hex_entry.get()
        self.destroy()


class SMTPConfigDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Configuration SMTP")
        self.geometry("420x380")
        self.resizable(False, False)
        self.config = load_smtp_config()
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text="⚙️ Configuration SMTP", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
        
        fields = [("Serveur:", "host", 200), ("Port:", "port", 80), ("Email:", "username", 200),
                  ("Mot de passe:", "password", 200), ("Nom expéditeur:", "from_name", 200)]
        self.entries = {}
        for label, key, width in fields:
            row = ctk.CTkFrame(main, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=label, width=110).pack(side="left")
            show = "*" if key == "password" else ""
            entry = ctk.CTkEntry(row, width=width, show=show)
            entry.pack(side="left")
            entry.insert(0, str(self.config.get(key, "")))
            self.entries[key] = entry
        
        row_ssl = ctk.CTkFrame(main, fg_color="transparent")
        row_ssl.pack(fill="x", pady=5)
        self.ssl_var = ctk.BooleanVar(value=self.config['use_ssl'])
        ctk.CTkCheckBox(row_ssl, text="SSL/TLS", variable=self.ssl_var).pack(side="left", padx=110)
        
        self.status = ctk.CTkLabel(main, text="", text_color=KRYSTO_SECONDARY)
        self.status.pack(pady=10)
        
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="🔌 Tester", width=90, command=self._test).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", width=90, command=self.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Sauver", fg_color=KRYSTO_PRIMARY, width=90, command=self._save).pack(side="left", padx=5)
    
    def _get_config(self):
        return {'host': self.entries['host'].get(), 'port': int(self.entries['port'].get() or 465),
                'use_ssl': self.ssl_var.get(), 'username': self.entries['username'].get(),
                'password': self.entries['password'].get(), 'from_name': self.entries['from_name'].get()}
    
    def _test(self):
        self.status.configure(text="Test...", text_color="#ffc107")
        self.update()
        success, msg = EmailService(self._get_config()).test_connection()
        self.status.configure(text=f"{'✅' if success else '❌'} {msg[:40]}", text_color=KRYSTO_SECONDARY if success else "#ff6b6b")
    
    def _save(self):
        if save_smtp_config(self._get_config()):
            self.status.configure(text="✅ Sauvegardé!", text_color=KRYSTO_SECONDARY)
            self.after(800, self.destroy)
        else:
            self.status.configure(text="❌ Erreur", text_color="#ff6b6b")


class SettingsDialog(ctk.CTkToplevel):
    """Dialogue pour les paramètres globaux (catalogue, etc.)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Paramètres KRYSTO")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text="⚙️ Paramètres", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 20))
        
        # Section Catalogue
        cat_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        cat_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(cat_frame, text="📚 Catalogue téléchargeable", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=15, pady=10)
        
        ctk.CTkLabel(cat_frame, text="Lien URL du catalogue (PDF ou page web):").pack(anchor="w", padx=15)
        self.catalog_url_entry = ctk.CTkEntry(cat_frame, placeholder_text="https://drive.google.com/... ou https://krysto.io/catalogue.pdf")
        self.catalog_url_entry.pack(fill="x", padx=15, pady=(5, 10))
        
        # Charger la valeur actuelle
        current_url = get_catalog_url()
        if current_url:
            self.catalog_url_entry.insert(0, current_url)
        
        ctk.CTkLabel(cat_frame, text="💡 Ce lien sera utilisé dans les emails de nouveautés\net disponible via la variable {{catalog_url}}",
                     text_color="#888", font=("Helvetica", 10)).pack(anchor="w", padx=15, pady=(0, 15))
        
        # Section Variables disponibles
        vars_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        vars_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(vars_frame, text="📝 Variables pour mailings", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=15, pady=10)
        
        vars_text = """{{name}} - Nom du client
{{email}} - Email du client
{{date}} - Date du jour
{{catalog_url}} - Lien du catalogue
{{dette_m1}}, {{dette_m2}}, {{dette_m3}}, {{dette_m3plus}} - Dettes
{{dette_total}} - Total des dettes
{{blocage_message}} - Message si client bloqué"""
        
        ctk.CTkLabel(vars_frame, text=vars_text, text_color="#aaa", font=("Courier", 10),
                     justify="left").pack(anchor="w", padx=15, pady=(0, 15))
        
        # Boutons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="💾 Sauvegarder", fg_color=KRYSTO_PRIMARY, command=self._save).pack(side="left", expand=True, padx=5)
    
    def _save(self):
        # Sauvegarder le lien du catalogue
        catalog_url = self.catalog_url_entry.get().strip()
        set_catalog_url(catalog_url)
        
        messagebox.showinfo("Succès", "Paramètres sauvegardés!")
        self.destroy()


# ============================================================================
# ÉDITEUR DE BLOCS
# ============================================================================
class BlockEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, block_type, existing_block=None, on_save=None):
        super().__init__(parent)
        self.block_type = block_type
        self.existing_block = existing_block
        self.on_save = on_save
        self.result = None
        
        block_class = BLOCK_TYPES.get(block_type)
        self.title(f"Éditer: {block_class.BLOCK_NAME}" if block_class else "Bloc")
        self.geometry("550x750")
        self.minsize(500, 400)
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        # IMPORTANT: Pack buttons FIRST with side="bottom" so they're always visible
        btn_frame = ctk.CTkFrame(self, fg_color="#2a2a2a", height=60)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)
        
        ctk.CTkButton(btn_frame, text="❌ Annuler", fg_color="#666", width=150, height=40,
                      command=self.destroy).pack(side="left", padx=20, pady=10)
        ctk.CTkButton(btn_frame, text="💾 Valider", fg_color=KRYSTO_PRIMARY, width=150, height=40,
                      command=self._save).pack(side="right", padx=20, pady=10)
        
        # Scrollable content area - fills remaining space
        container = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        ui_method = getattr(self, f"_ui_{self.block_type}", None)
        if ui_method: 
            ui_method(container)
        else: 
            ctk.CTkLabel(container, text="Type non supporté").pack(pady=20)
    
    def _ui_text(self, p):
        ctk.CTkLabel(p, text="📝 Texte", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(p, text="Contenu:").pack(anchor="w")
        self.text_content = ctk.CTkTextbox(p, height=100)
        self.text_content.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Taille:").pack(side="left")
        self.font_size = ctk.CTkEntry(row1, width=50)
        self.font_size.pack(side="left", padx=5)
        self.bold_var, self.italic_var, self.underline_var = ctk.BooleanVar(), ctk.BooleanVar(), ctk.BooleanVar()
        ctk.CTkCheckBox(row1, text="B", variable=self.bold_var, width=50).pack(side="left")
        ctk.CTkCheckBox(row1, text="I", variable=self.italic_var, width=50).pack(side="left")
        ctk.CTkCheckBox(row1, text="U", variable=self.underline_var, width=50).pack(side="left")
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Couleur:").pack(side="left")
        self.text_color_btn = ctk.CTkButton(row2, text="", width=35, height=25, fg_color=KRYSTO_DARK,
                                             command=lambda: self._pick_color("text_color_btn"))
        self.text_color_btn.pack(side="left", padx=5)
        ctk.CTkLabel(row2, text="Fond:").pack(side="left", padx=(10, 0))
        self.bg_color_btn = ctk.CTkButton(row2, text="", width=35, height=25, fg_color="#f5f5f5",
                                           command=lambda: self._pick_color("bg_color_btn"))
        self.bg_color_btn.pack(side="left", padx=5)
        
        row3 = ctk.CTkFrame(p, fg_color="transparent")
        row3.pack(fill="x", pady=5)
        ctk.CTkLabel(row3, text="Alignement:").pack(side="left")
        self.align = ctk.CTkSegmentedButton(row3, values=["left", "center", "right"], width=180)
        self.align.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.text_content.insert("1.0", c.get('text', ''))
        self.font_size.insert(0, str(c.get('font_size', 15)))
        self.bold_var.set(c.get('bold', False))
        self.italic_var.set(c.get('italic', False))
        self.underline_var.set(c.get('underline', False))
        self.text_color_btn.configure(fg_color=c.get('color', KRYSTO_DARK))
        self.bg_color_btn.configure(fg_color=c.get('background', '#f5f5f5'))
        self.align.set(c.get('align', 'left'))
    
    def _ui_title(self, p):
        ctk.CTkLabel(p, text="📌 Titre", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(p, text="Texte:").pack(anchor="w")
        self.title_text = ctk.CTkEntry(p, height=38)
        self.title_text.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Niveau:").pack(side="left")
        self.title_level = ctk.CTkSegmentedButton(row1, values=["h1", "h2", "h3"], width=150)
        self.title_level.pack(side="left", padx=10)
        ctk.CTkLabel(row1, text="Taille:").pack(side="left")
        self.title_size = ctk.CTkEntry(row1, width=50)
        self.title_size.pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Alignement:").pack(side="left")
        self.title_align = ctk.CTkSegmentedButton(row2, values=["left", "center", "right"], width=180)
        self.title_align.pack(side="left", padx=10)
        
        row3 = ctk.CTkFrame(p, fg_color="transparent")
        row3.pack(fill="x", pady=5)
        ctk.CTkLabel(row3, text="Souligné:").pack(side="left")
        self.underline_style = ctk.CTkSegmentedButton(row3, values=["none", "gradient", "solid"], width=200)
        self.underline_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.title_text.insert(0, c.get('text', ''))
        self.title_level.set(c.get('level', 'h2'))
        self.title_size.insert(0, str(c.get('font_size', 24)))
        self.title_align.set(c.get('align', 'left'))
        self.underline_style.set(c.get('underline_style', 'gradient'))
    
    def _ui_image(self, p):
        ctk.CTkLabel(p, text="🖼️ Image", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(p, text="URL:").pack(anchor="w")
        self.image_url = ctk.CTkEntry(p, height=35, placeholder_text="https://...")
        self.image_url.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Largeur:").pack(side="left")
        self.image_width = ctk.CTkEntry(row1, width=70, placeholder_text="100%")
        self.image_width.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Arrondi:").pack(side="left")
        self.image_radius = ctk.CTkEntry(row1, width=50)
        self.image_radius.pack(side="left", padx=5)
        self.image_shadow = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row1, text="Ombre", variable=self.image_shadow).pack(side="left", padx=10)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Alignement:").pack(side="left")
        self.image_align = ctk.CTkSegmentedButton(row2, values=["left", "center", "right"], width=180)
        self.image_align.pack(side="left", padx=10)
        
        ctk.CTkLabel(p, text="Légende:").pack(anchor="w", pady=(10, 0))
        self.image_caption = ctk.CTkEntry(p, height=30)
        self.image_caption.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Lien au clic:").pack(anchor="w")
        self.image_link = ctk.CTkEntry(p, height=30, placeholder_text="https://...")
        self.image_link.pack(fill="x", pady=5)
        
        c = self.existing_block.content if self.existing_block else {}
        self.image_url.insert(0, c.get('url', ''))
        self.image_width.insert(0, c.get('width', '100%'))
        self.image_radius.insert(0, str(c.get('border_radius', 12)))
        self.image_shadow.set(c.get('shadow', True))
        self.image_align.set(c.get('align', 'center'))
        self.image_caption.insert(0, c.get('caption', ''))
        self.image_link.insert(0, c.get('link_url', ''))
    
    def _ui_button(self, p):
        ctk.CTkLabel(p, text="🔘 Bouton", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(p, text="Texte:").pack(anchor="w")
        self.btn_text = ctk.CTkEntry(p, height=38)
        self.btn_text.pack(fill="x", pady=5)
        ctk.CTkLabel(p, text="URL:").pack(anchor="w")
        self.btn_url = ctk.CTkEntry(p, height=35, placeholder_text="https://...")
        self.btn_url.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Style:").pack(side="left")
        self.btn_style = ctk.CTkSegmentedButton(row1, values=["gradient", "solid", "outline"], width=200)
        self.btn_style.pack(side="left", padx=10)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Icône:").pack(side="left")
        self.btn_icon = ctk.CTkEntry(row2, width=50, placeholder_text="🚀")
        self.btn_icon.pack(side="left", padx=5)
        ctk.CTkLabel(row2, text="Align:").pack(side="left")
        self.btn_align = ctk.CTkSegmentedButton(row2, values=["left", "center", "right"], width=150)
        self.btn_align.pack(side="left", padx=10)
        
        row3 = ctk.CTkFrame(p, fg_color="transparent")
        row3.pack(fill="x", pady=5)
        self.btn_shadow = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row3, text="Ombre", variable=self.btn_shadow).pack(side="left")
        self.btn_full_width = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row3, text="Pleine largeur", variable=self.btn_full_width).pack(side="left", padx=15)
        
        c = self.existing_block.content if self.existing_block else {}
        self.btn_text.insert(0, c.get('text', 'Cliquez ici'))
        self.btn_url.insert(0, c.get('url', ''))
        self.btn_style.set(c.get('style', 'gradient'))
        self.btn_icon.insert(0, c.get('icon', ''))
        self.btn_align.set(c.get('align', 'center'))
        self.btn_shadow.set(c.get('shadow', True))
        self.btn_full_width.set(c.get('full_width', False))
    
    def _ui_divider(self, p):
        ctk.CTkLabel(p, text="➖ Séparateur", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=10)
        ctk.CTkLabel(row1, text="Style:").pack(side="left")
        self.divider_style = ctk.CTkSegmentedButton(row1, values=["gradient", "solid", "dashed", "dotted"], width=280)
        self.divider_style.pack(side="left", padx=10)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Couleur:").pack(side="left")
        self.divider_color = ctk.CTkButton(row2, text="", width=35, height=25, fg_color=KRYSTO_SECONDARY,
                                            command=lambda: self._pick_color("divider_color"))
        self.divider_color.pack(side="left", padx=5)
        ctk.CTkLabel(row2, text="Hauteur:").pack(side="left", padx=(15, 0))
        self.divider_height = ctk.CTkEntry(row2, width=50)
        self.divider_height.pack(side="left", padx=5)
        
        c = self.existing_block.content if self.existing_block else {}
        self.divider_style.set(c.get('style', 'gradient'))
        self.divider_color.configure(fg_color=c.get('color', KRYSTO_SECONDARY))
        self.divider_height.insert(0, str(c.get('height', 3)))
    
    def _ui_spacer(self, p):
        ctk.CTkLabel(p, text="📏 Espace", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(p, text="Hauteur (px):").pack(anchor="w")
        self.spacer_height = ctk.CTkEntry(p, width=100)
        self.spacer_height.pack(anchor="w", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(anchor="w", pady=10)
        for h in [10, 20, 30, 50, 80]:
            ctk.CTkButton(row, text=f"{h}", width=45, fg_color="gray",
                          command=lambda v=h: self._set_val(self.spacer_height, v)).pack(side="left", padx=2)
        
        c = self.existing_block.content if self.existing_block else {}
        self.spacer_height.insert(0, str(c.get('height', 30)))
    
    def _ui_quote(self, p):
        ctk.CTkLabel(p, text="💬 Citation", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(p, text="Texte:").pack(anchor="w")
        self.quote_text = ctk.CTkTextbox(p, height=80)
        self.quote_text.pack(fill="x", pady=5)
        ctk.CTkLabel(p, text="Auteur:").pack(anchor="w")
        self.quote_author = ctk.CTkEntry(p, height=30)
        self.quote_author.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.quote_style = ctk.CTkSegmentedButton(row, values=["modern", "minimal"], width=150)
        self.quote_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.quote_text.insert("1.0", c.get('text', ''))
        self.quote_author.insert(0, c.get('author', ''))
        self.quote_style.set(c.get('style', 'modern'))
    
    def _ui_list(self, p):
        ctk.CTkLabel(p, text="📋 Liste", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.list_style = ctk.CTkSegmentedButton(row, values=["icons", "bullets", "numbers", "check"], width=260)
        self.list_style.pack(side="left", padx=10)
        
        ctk.CTkLabel(p, text="Éléments (un par ligne, format: icône | texte):").pack(anchor="w", pady=(10, 5))
        self.list_items = ctk.CTkTextbox(p, height=150)
        self.list_items.pack(fill="x")
        
        c = self.existing_block.content if self.existing_block else {}
        self.list_style.set(c.get('style', 'icons'))
        items_text = "\n".join(f"{it.get('icon', '✓')} | {it['text']}" for it in c.get('items', []))
        self.list_items.insert("1.0", items_text)
    
    def _ui_promo_code(self, p):
        ctk.CTkLabel(p, text="🎁 Code Promo", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(p, text="Code:").pack(anchor="w")
        self.promo_code = ctk.CTkEntry(p, height=40, font=("Helvetica", 16, "bold"))
        self.promo_code.pack(fill="x", pady=5)
        ctk.CTkLabel(p, text="Description:").pack(anchor="w")
        self.promo_desc = ctk.CTkEntry(p, height=35)
        self.promo_desc.pack(fill="x", pady=5)
        ctk.CTkLabel(p, text="Expiration:").pack(anchor="w")
        self.promo_expiry = ctk.CTkEntry(p, height=30, placeholder_text="31/12/2025")
        self.promo_expiry.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.promo_style = ctk.CTkSegmentedButton(row, values=["card", "minimal"], width=150)
        self.promo_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.promo_code.insert(0, c.get('code', 'KRYSTO20'))
        self.promo_desc.insert(0, c.get('description', ''))
        self.promo_expiry.insert(0, c.get('expiry', ''))
        self.promo_style.set(c.get('style', 'card'))
    
    def _ui_social(self, p):
        ctk.CTkLabel(p, text="🔗 Réseaux Sociaux", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Style
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.social_style = ctk.CTkSegmentedButton(row, values=["colored", "mono", "outline"], width=200)
        self.social_style.pack(side="left", padx=10)
        
        # Taille
        ctk.CTkLabel(row, text="Taille:").pack(side="left", padx=(20, 5))
        self.social_size = ctk.CTkEntry(row, width=50, placeholder_text="40")
        self.social_size.pack(side="left")
        
        ctk.CTkLabel(p, text="Entrez l'URL de chaque réseau à afficher (laisser vide pour masquer):",
                     text_color="#888", font=("Helvetica", 10)).pack(anchor="w", pady=5)
        
        # Liste des réseaux scrollable
        networks_frame = ctk.CTkScrollableFrame(p, height=200, fg_color="#1a1a1a")
        networks_frame.pack(fill="both", expand=True, pady=5)
        
        self.social_entries = {}
        for net_id, net_info in SOCIAL_NETWORKS.items():
            row = ctk.CTkFrame(networks_frame, fg_color="#2a2a2a")
            row.pack(fill="x", pady=2, padx=2)
            
            # Icône colorée
            color_box = ctk.CTkFrame(row, width=20, height=20, fg_color=net_info['color'], corner_radius=4)
            color_box.pack(side="left", padx=8, pady=8)
            color_box.pack_propagate(False)
            
            ctk.CTkLabel(row, text=net_info['name'], width=90, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, placeholder_text=net_info['placeholder'])
            entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
            self.social_entries[net_id] = entry
        
        # Charger les valeurs existantes
        c = self.existing_block.content if self.existing_block else {}
        self.social_style.set(c.get('style', 'colored'))
        self.social_size.insert(0, str(c.get('size', 40)))
        
        networks = c.get('networks', {})
        if isinstance(networks, dict):
            for net_id, url in networks.items():
                if net_id in self.social_entries and url:
                    self.social_entries[net_id].insert(0, url)
        elif isinstance(networks, list):
            # Ancien format - compatibilité
            for net in networks:
                net_name = net.get('name', '')
                if net_name in self.social_entries:
                    self.social_entries[net_name].insert(0, net.get('url', ''))
    
    def _ui_html(self, p):
        ctk.CTkLabel(p, text="🔧 HTML", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(p, text="Code HTML:").pack(anchor="w")
        self.html_content = ctk.CTkTextbox(p, height=250)
        self.html_content.pack(fill="both", expand=True)
        
        c = self.existing_block.content if self.existing_block else {}
        self.html_content.insert("1.0", c.get('html', ''))
    
    def _ui_image_grid(self, p):
        ctk.CTkLabel(p, text="🖼️ Grille d'Images", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Colonnes:").pack(side="left")
        self.grid_cols = ctk.CTkSegmentedButton(row1, values=["2", "3", "4"], width=150)
        self.grid_cols.pack(side="left", padx=10)
        ctk.CTkLabel(row1, text="Écart:").pack(side="left")
        self.grid_gap = ctk.CTkEntry(row1, width=50)
        self.grid_gap.pack(side="left", padx=5)
        
        ctk.CTkLabel(p, text="Images (URL | légende | lien, une par ligne):").pack(anchor="w", pady=(10, 5))
        self.grid_images = ctk.CTkTextbox(p, height=150)
        self.grid_images.pack(fill="x")
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        self.grid_shadow = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row2, text="Ombre", variable=self.grid_shadow).pack(side="left")
        self.grid_captions = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row2, text="Légendes", variable=self.grid_captions).pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.grid_cols.set(str(c.get('columns', 2)))
        self.grid_gap.insert(0, str(c.get('gap', 15)))
        self.grid_shadow.set(c.get('shadow', True))
        self.grid_captions.set(c.get('captions', True))
        imgs_text = "\n".join(f"{i.get('url','')} | {i.get('caption','')} | {i.get('link','')}" for i in c.get('images', []))
        self.grid_images.insert("1.0", imgs_text)
    
    def _ui_hero(self, p):
        ctk.CTkLabel(p, text="🎯 Image Héro", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Image URL:").pack(anchor="w")
        self.hero_image = ctk.CTkEntry(p, height=35, placeholder_text="https://...")
        self.hero_image.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Titre:").pack(anchor="w")
        self.hero_title = ctk.CTkEntry(p, height=38, font=("Helvetica", 14, "bold"))
        self.hero_title.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Sous-titre:").pack(anchor="w")
        self.hero_subtitle = ctk.CTkTextbox(p, height=60)
        self.hero_subtitle.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Hauteur:").pack(side="left")
        self.hero_height = ctk.CTkEntry(row1, width=60)
        self.hero_height.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Alignement:").pack(side="left", padx=(15, 0))
        self.hero_align = ctk.CTkSegmentedButton(row1, values=["left", "center", "right"], width=150)
        self.hero_align.pack(side="left", padx=10)
        
        ctk.CTkLabel(p, text="Bouton (texte | URL):").pack(anchor="w", pady=(10, 0))
        self.hero_btn = ctk.CTkEntry(p, height=30, placeholder_text="Découvrir | https://...")
        self.hero_btn.pack(fill="x", pady=5)
        
        c = self.existing_block.content if self.existing_block else {}
        self.hero_image.insert(0, c.get('image_url', ''))
        self.hero_title.insert(0, c.get('title', ''))
        self.hero_subtitle.insert("1.0", c.get('subtitle', ''))
        self.hero_height.insert(0, str(c.get('height', 400)))
        self.hero_align.set(c.get('text_align', 'center'))
        if c.get('button_text'): self.hero_btn.insert(0, f"{c['button_text']} | {c.get('button_url', '')}")
    
    def _ui_card(self, p):
        ctk.CTkLabel(p, text="🃏 Carte", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Image URL:").pack(anchor="w")
        self.card_image = ctk.CTkEntry(p, height=30, placeholder_text="https://...")
        self.card_image.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Titre:").pack(anchor="w")
        self.card_title = ctk.CTkEntry(p, height=35)
        self.card_title.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Description:").pack(anchor="w")
        self.card_desc = ctk.CTkTextbox(p, height=60)
        self.card_desc.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Bouton (texte | URL):").pack(anchor="w")
        self.card_btn = ctk.CTkEntry(p, height=30, placeholder_text="En savoir plus | https://...")
        self.card_btn.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        self.card_shadow = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row, text="Ombre", variable=self.card_shadow).pack(side="left")
        ctk.CTkLabel(row, text="Image:").pack(side="left", padx=(15, 0))
        self.card_img_pos = ctk.CTkSegmentedButton(row, values=["top", "bottom"], width=120)
        self.card_img_pos.pack(side="left", padx=5)
        
        c = self.existing_block.content if self.existing_block else {}
        self.card_image.insert(0, c.get('image_url', ''))
        self.card_title.insert(0, c.get('title', ''))
        self.card_desc.insert("1.0", c.get('description', ''))
        if c.get('button_text'): self.card_btn.insert(0, f"{c['button_text']} | {c.get('button_url', '')}")
        self.card_shadow.set(c.get('shadow', True))
        self.card_img_pos.set(c.get('image_position', 'top'))
    
    def _ui_columns(self, p):
        ctk.CTkLabel(p, text="📊 Colonnes", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="💡 Entrez du HTML ou du texte simple dans chaque colonne",
                     text_color="#888", font=("Helvetica", 10)).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Colonne 1:").pack(anchor="w", pady=(5, 0))
        self.col1_content = ctk.CTkTextbox(p, height=100)
        self.col1_content.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Colonne 2:").pack(anchor="w", pady=(5, 0))
        self.col2_content = ctk.CTkTextbox(p, height=100)
        self.col2_content.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=10)
        ctk.CTkLabel(row, text="Proportions:").pack(side="left")
        self.col_ratio = ctk.CTkSegmentedButton(row, values=["50/50", "40/60", "60/40", "30/70"], width=220)
        self.col_ratio.pack(side="left", padx=10)
        
        # Charger le contenu existant
        c = self.existing_block.content if self.existing_block else {}
        cols = c.get('columns', [{'content': ''}, {'content': ''}])
        if len(cols) > 0: 
            self.col1_content.insert("1.0", cols[0].get('content', ''))
        if len(cols) > 1: 
            self.col2_content.insert("1.0", cols[1].get('content', ''))
        
        # Détecter la proportion existante
        if len(cols) >= 2:
            w1 = cols[0].get('width', '50%')
            if '40' in w1: self.col_ratio.set("40/60")
            elif '60' in w1: self.col_ratio.set("60/40")
            elif '30' in w1: self.col_ratio.set("30/70")
            else: self.col_ratio.set("50/50")
        else:
            self.col_ratio.set("50/50")
    
    def _ui_product(self, p):
        ctk.CTkLabel(p, text="🛍️ Produit", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Image URL:").pack(anchor="w")
        self.prod_image = ctk.CTkEntry(p, height=30, placeholder_text="https://...")
        self.prod_image.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Nom:").pack(anchor="w")
        self.prod_name = ctk.CTkEntry(p, height=35)
        self.prod_name.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Description:").pack(anchor="w")
        self.prod_desc = ctk.CTkTextbox(p, height=50)
        self.prod_desc.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Prix:").pack(side="left")
        self.prod_price = ctk.CTkEntry(row1, width=100, placeholder_text="15 000 XPF")
        self.prod_price.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Ancien:").pack(side="left")
        self.prod_old_price = ctk.CTkEntry(row1, width=100, placeholder_text="20 000 XPF")
        self.prod_old_price.pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Badge:").pack(side="left")
        self.prod_badge = ctk.CTkEntry(row2, width=100, placeholder_text="-25%")
        self.prod_badge.pack(side="left", padx=5)
        ctk.CTkLabel(row2, text="CTA URL:").pack(side="left")
        self.prod_cta = ctk.CTkEntry(row2, placeholder_text="https://...")
        self.prod_cta.pack(side="left", fill="x", expand=True, padx=5)
        
        c = self.existing_block.content if self.existing_block else {}
        self.prod_image.insert(0, c.get('image_url', ''))
        self.prod_name.insert(0, c.get('name', ''))
        self.prod_desc.insert("1.0", c.get('description', ''))
        self.prod_price.insert(0, c.get('price', ''))
        self.prod_old_price.insert(0, c.get('old_price', ''))
        self.prod_badge.insert(0, c.get('badge', ''))
        self.prod_cta.insert(0, c.get('cta_url', ''))
    
    def _ui_testimonial(self, p):
        ctk.CTkLabel(p, text="💬 Témoignage", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Citation:").pack(anchor="w")
        self.testi_quote = ctk.CTkTextbox(p, height=80)
        self.testi_quote.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Nom:").pack(side="left")
        self.testi_name = ctk.CTkEntry(row1, width=150)
        self.testi_name.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Titre:").pack(side="left")
        self.testi_title = ctk.CTkEntry(row1, placeholder_text="CEO, Entreprise")
        self.testi_title.pack(side="left", fill="x", expand=True, padx=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Photo URL:").pack(side="left")
        self.testi_photo = ctk.CTkEntry(row2, placeholder_text="https://...")
        self.testi_photo.pack(side="left", fill="x", expand=True, padx=5)
        
        row3 = ctk.CTkFrame(p, fg_color="transparent")
        row3.pack(fill="x", pady=5)
        ctk.CTkLabel(row3, text="Étoiles:").pack(side="left")
        self.testi_stars = ctk.CTkSegmentedButton(row3, values=["0", "3", "4", "5"], width=150)
        self.testi_stars.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.testi_quote.insert("1.0", c.get('quote', ''))
        self.testi_name.insert(0, c.get('author_name', ''))
        self.testi_title.insert(0, c.get('author_title', ''))
        self.testi_photo.insert(0, c.get('author_image', ''))
        self.testi_stars.set(str(c.get('rating', 5)))
    
    def _ui_video(self, p):
        ctk.CTkLabel(p, text="🎬 Vidéo", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="URL miniature:").pack(anchor="w")
        self.video_thumb = ctk.CTkEntry(p, height=30, placeholder_text="https://...")
        self.video_thumb.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="URL vidéo:").pack(anchor="w")
        self.video_url = ctk.CTkEntry(p, height=30, placeholder_text="https://youtube.com/...")
        self.video_url.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Titre:").pack(anchor="w")
        self.video_title = ctk.CTkEntry(p, height=30)
        self.video_title.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Durée:").pack(anchor="w")
        self.video_duration = ctk.CTkEntry(p, width=80, placeholder_text="3:45")
        self.video_duration.pack(anchor="w", pady=5)
        
        c = self.existing_block.content if self.existing_block else {}
        self.video_thumb.insert(0, c.get('thumbnail_url', ''))
        self.video_url.insert(0, c.get('video_url', ''))
        self.video_title.insert(0, c.get('title', ''))
        self.video_duration.insert(0, c.get('duration', ''))
    
    def _ui_countdown(self, p):
        ctk.CTkLabel(p, text="⏱️ Compte à rebours", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Titre:").pack(anchor="w")
        self.countdown_title = ctk.CTkEntry(p, height=30)
        self.countdown_title.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=10)
        for attr, label in [("countdown_days", "Jours"), ("countdown_hours", "Heures"), ("countdown_mins", "Minutes")]:
            ctk.CTkLabel(row, text=f"{label}:").pack(side="left")
            entry = ctk.CTkEntry(row, width=50)
            entry.pack(side="left", padx=(5, 15))
            setattr(self, attr, entry)
        
        c = self.existing_block.content if self.existing_block else {}
        self.countdown_title.insert(0, c.get('title', 'Offre expire dans:'))
        self.countdown_days.insert(0, c.get('days', '03'))
        self.countdown_hours.insert(0, c.get('hours', '12'))
        self.countdown_mins.insert(0, c.get('minutes', '45'))
    
    def _ui_gallery(self, p):
        ctk.CTkLabel(p, text="🎨 Galerie", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Images (URL | lien, une par ligne, 1ère = principale):").pack(anchor="w")
        self.gallery_images = ctk.CTkTextbox(p, height=120)
        self.gallery_images.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Légende:").pack(anchor="w")
        self.gallery_caption = ctk.CTkEntry(p, height=30)
        self.gallery_caption.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Hauteur img principale:").pack(side="left")
        self.gallery_height = ctk.CTkEntry(row, width=60)
        self.gallery_height.pack(side="left", padx=5)
        
        c = self.existing_block.content if self.existing_block else {}
        imgs_text = "\n".join(f"{i.get('url','')} | {i.get('link','')}" for i in c.get('images', []))
        self.gallery_images.insert("1.0", imgs_text)
        self.gallery_caption.insert(0, c.get('caption', ''))
        self.gallery_height.insert(0, str(c.get('main_height', 350)))
    
    def _ui_accordion(self, p):
        ctk.CTkLabel(p, text="📚 FAQ / Accordéon", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Questions/Réponses (Q: ... puis R: ...):").pack(anchor="w")
        self.accordion_items = ctk.CTkTextbox(p, height=200)
        self.accordion_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.accordion_style = ctk.CTkSegmentedButton(row, values=["bordered", "minimal"], width=150)
        self.accordion_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        items_text = ""
        for item in c.get('items', []):
            items_text += f"Q: {item.get('question', '')}\nR: {item.get('answer', '')}\n\n"
        self.accordion_items.insert("1.0", items_text.strip())
        self.accordion_style.set(c.get('style', 'bordered'))
    
    def _ui_stats(self, p):
        ctk.CTkLabel(p, text="📈 Statistiques", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Stats (valeur | label, une par ligne):").pack(anchor="w")
        self.stats_items = ctk.CTkTextbox(p, height=100)
        self.stats_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Colonnes:").pack(side="left")
        self.stats_cols = ctk.CTkSegmentedButton(row, values=["2", "3", "4"], width=150)
        self.stats_cols.pack(side="left", padx=10)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.stats_style = ctk.CTkSegmentedButton(row, values=["cards", "minimal"], width=150)
        self.stats_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        stats_text = "\n".join(f"{s.get('value','')} | {s.get('label','')}" for s in c.get('stats', []))
        self.stats_items.insert("1.0", stats_text or "100+ | Clients\n500 | Projets")
        self.stats_cols.set(str(c.get('columns', 3)))
        self.stats_style.set(c.get('style', 'cards'))
    
    def _ui_map(self, p):
        ctk.CTkLabel(p, text="📍 Carte Google Maps", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Adresse:").pack(anchor="w")
        self.map_address = ctk.CTkEntry(p, height=30)
        self.map_address.pack(fill="x", pady=5)
        
        # Options
        opts_frame = ctk.CTkFrame(p, fg_color="#1a1a1a")
        opts_frame.pack(fill="x", pady=10)
        
        row1 = ctk.CTkFrame(opts_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="Type:").pack(side="left")
        self.map_type = ctk.CTkSegmentedButton(row1, values=["roadmap", "satellite", "terrain"], width=200)
        self.map_type.pack(side="left", padx=10)
        ctk.CTkLabel(row1, text="Zoom:").pack(side="left", padx=(20, 5))
        self.map_zoom = ctk.CTkEntry(row1, width=50, placeholder_text="15")
        self.map_zoom.pack(side="left")
        
        self.map_show_address = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opts_frame, text="Afficher l'adresse sur la carte", 
                        variable=self.map_show_address).pack(anchor="w", padx=10, pady=5)
        
        # Image URL (optionnel si pas de clé API)
        img_frame = ctk.CTkFrame(p, fg_color="#2a2a2a")
        img_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(img_frame, text="🖼️ Image de la carte", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=5)
        ctk.CTkLabel(img_frame, text="Option 1: Clé API Google Maps (génère la carte automatiquement):",
                     text_color="#888", font=("Helvetica", 9)).pack(anchor="w", padx=10)
        self.map_api_key = ctk.CTkEntry(img_frame, height=28, placeholder_text="AIza...")
        self.map_api_key.pack(fill="x", padx=10, pady=3)
        
        ctk.CTkLabel(img_frame, text="Option 2: URL d'une capture d'écran (si pas de clé API):",
                     text_color="#888", font=("Helvetica", 9)).pack(anchor="w", padx=10)
        self.map_image = ctk.CTkEntry(img_frame, height=28, placeholder_text="https://...")
        self.map_image.pack(fill="x", padx=10, pady=(3, 10))
        
        # Astuce
        tip = ctk.CTkLabel(p, text="💡 Sans image ni clé API, une carte placeholder sera affichée.\n" +
                           "Pour faire une capture: Google Maps → clic droit → 'Copier l'image'",
                     text_color="#888", font=("Helvetica", 9), justify="left")
        tip.pack(anchor="w", pady=5)
        
        # Charger valeurs
        c = self.existing_block.content if self.existing_block else {}
        self.map_address.insert(0, c.get('address', COMPANY_ADDRESS))
        self.map_type.set(c.get('map_type', 'roadmap'))
        self.map_zoom.insert(0, str(c.get('zoom', 15)))
        self.map_show_address.set(c.get('show_address', True))
        self.map_api_key.insert(0, c.get('api_key', ''))
        self.map_image.insert(0, c.get('image_url', ''))
    
    def _ui_footer_links(self, p):
        ctk.CTkLabel(p, text="🔗 Liens Footer", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Liens (texte | URL, un par ligne):").pack(anchor="w")
        self.footer_links_items = ctk.CTkTextbox(p, height=120)
        self.footer_links_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Séparateur:").pack(side="left")
        self.footer_sep = ctk.CTkEntry(row, width=50)
        self.footer_sep.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="Align:").pack(side="left")
        self.footer_align = ctk.CTkSegmentedButton(row, values=["left", "center", "right"], width=150)
        self.footer_align.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        links_text = "\n".join(f"{l.get('text','')} | {l.get('url','')}" for l in c.get('links', []))
        self.footer_links_items.insert("1.0", links_text or f"Site web | https://{COMPANY_WEBSITE}\nContact | mailto:{COMPANY_EMAIL}")
        self.footer_sep.insert(0, c.get('separator', ' | '))
        self.footer_align.set(c.get('align', 'center'))
    
    def _ui_unsubscribe(self, p):
        ctk.CTkLabel(p, text="🚫 Désinscription", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Texte du lien:").pack(anchor="w")
        self.unsub_text = ctk.CTkEntry(p, height=30)
        self.unsub_text.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Email admin (notifications):").pack(anchor="w")
        self.unsub_email = ctk.CTkEntry(p, height=30)
        self.unsub_email.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.unsub_style = ctk.CTkSegmentedButton(row, values=["link", "button", "discrete"], width=200)
        self.unsub_style.pack(side="left", padx=10)
        
        self.unsub_show_info = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(p, text="Afficher texte explicatif", variable=self.unsub_show_info).pack(anchor="w", pady=5)
        
        ctk.CTkLabel(p, text="Texte explicatif:").pack(anchor="w")
        self.unsub_info = ctk.CTkEntry(p, height=30)
        self.unsub_info.pack(fill="x", pady=5)
        
        # Info
        info_frame = ctk.CTkFrame(p, fg_color="#1a3a1a")
        info_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(info_frame, text="ℹ️ Fonctionnement:", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=5)
        ctk.CTkLabel(info_frame, text="• Quand le client clique, un email est envoyé à l'admin\n• Le client voit une page de confirmation\n• L'email contient les infos du client à désinscrire",
                     text_color="#888", font=("Helvetica", 10), justify="left").pack(anchor="w", padx=10, pady=(0, 10))
        
        c = self.existing_block.content if self.existing_block else {}
        self.unsub_text.insert(0, c.get('text', 'Se désinscrire'))
        self.unsub_email.insert(0, c.get('admin_email', 'contact@krysto.nc'))
        self.unsub_style.set(c.get('style', 'link'))
        self.unsub_show_info.set(c.get('show_info', True))
        self.unsub_info.insert(0, c.get('info_text', 'Vous ne souhaitez plus recevoir nos emails ?'))
    
    def _ui_signature(self, p):
        ctk.CTkLabel(p, text="✍️ Signature Email", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=3)
        ctk.CTkLabel(row1, text="Nom:", width=80).pack(side="left")
        self.sig_name = ctk.CTkEntry(row1)
        self.sig_name.pack(side="left", fill="x", expand=True, padx=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=3)
        ctk.CTkLabel(row2, text="Fonction:", width=80).pack(side="left")
        self.sig_title = ctk.CTkEntry(row2)
        self.sig_title.pack(side="left", fill="x", expand=True, padx=5)
        
        row3 = ctk.CTkFrame(p, fg_color="transparent")
        row3.pack(fill="x", pady=3)
        ctk.CTkLabel(row3, text="Entreprise:", width=80).pack(side="left")
        self.sig_company = ctk.CTkEntry(row3)
        self.sig_company.pack(side="left", fill="x", expand=True, padx=5)
        
        row4 = ctk.CTkFrame(p, fg_color="transparent")
        row4.pack(fill="x", pady=3)
        ctk.CTkLabel(row4, text="Téléphone:", width=80).pack(side="left")
        self.sig_phone = ctk.CTkEntry(row4)
        self.sig_phone.pack(side="left", fill="x", expand=True, padx=5)
        
        row5 = ctk.CTkFrame(p, fg_color="transparent")
        row5.pack(fill="x", pady=3)
        ctk.CTkLabel(row5, text="Email:", width=80).pack(side="left")
        self.sig_email = ctk.CTkEntry(row5)
        self.sig_email.pack(side="left", fill="x", expand=True, padx=5)
        
        row6 = ctk.CTkFrame(p, fg_color="transparent")
        row6.pack(fill="x", pady=3)
        ctk.CTkLabel(row6, text="Site web:", width=80).pack(side="left")
        self.sig_website = ctk.CTkEntry(row6)
        self.sig_website.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(p, text="URL photo (optionnel):").pack(anchor="w", pady=(10, 0))
        self.sig_photo = ctk.CTkEntry(p, placeholder_text="https://...")
        self.sig_photo.pack(fill="x", pady=3)
        
        row7 = ctk.CTkFrame(p, fg_color="transparent")
        row7.pack(fill="x", pady=5)
        ctk.CTkLabel(row7, text="Style:").pack(side="left")
        self.sig_style = ctk.CTkSegmentedButton(row7, values=["modern", "classic", "minimal"], width=200)
        self.sig_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.sig_name.insert(0, c.get('name', "L'équipe KRYSTO"))
        self.sig_title.insert(0, c.get('title', ''))
        self.sig_company.insert(0, c.get('company', COMPANY_NAME))
        self.sig_phone.insert(0, c.get('phone', COMPANY_PHONE))
        self.sig_email.insert(0, c.get('email', COMPANY_EMAIL))
        self.sig_website.insert(0, c.get('website', COMPANY_WEBSITE))
        self.sig_photo.insert(0, c.get('photo_url', ''))
        self.sig_style.set(c.get('style', 'modern'))
    
    def _ui_alert(self, p):
        ctk.CTkLabel(p, text="⚠️ Alerte / Notification", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Texte:").pack(anchor="w")
        self.alert_text = ctk.CTkEntry(p, height=30)
        self.alert_text.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Type:").pack(side="left")
        self.alert_type = ctk.CTkSegmentedButton(row1, values=["info", "success", "warning", "error", "promo"], width=280)
        self.alert_type.pack(side="left", padx=10)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Style:").pack(side="left")
        self.alert_style = ctk.CTkSegmentedButton(row2, values=["banner", "card", "minimal"], width=200)
        self.alert_style.pack(side="left", padx=10)
        
        ctk.CTkLabel(p, text="Icône (auto = selon type):").pack(anchor="w", pady=(10, 0))
        self.alert_icon = ctk.CTkEntry(p, placeholder_text="auto")
        self.alert_icon.pack(fill="x", pady=3)
        
        c = self.existing_block.content if self.existing_block else {}
        self.alert_text.insert(0, c.get('text', 'Information importante'))
        self.alert_type.set(c.get('type', 'info'))
        self.alert_style.set(c.get('style', 'banner'))
        self.alert_icon.insert(0, c.get('icon', 'auto'))
    
    def _ui_pricing(self, p):
        ctk.CTkLabel(p, text="💎 Tarification", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=3)
        ctk.CTkLabel(row1, text="Nom offre:", width=80).pack(side="left")
        self.pricing_name = ctk.CTkEntry(row1)
        self.pricing_name.pack(side="left", fill="x", expand=True, padx=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=3)
        ctk.CTkLabel(row2, text="Prix:", width=80).pack(side="left")
        self.pricing_price = ctk.CTkEntry(row2, width=100)
        self.pricing_price.pack(side="left", padx=5)
        self.pricing_currency = ctk.CTkEntry(row2, width=60, placeholder_text="XPF")
        self.pricing_currency.pack(side="left", padx=5)
        self.pricing_period = ctk.CTkEntry(row2, width=80, placeholder_text="/mois")
        self.pricing_period.pack(side="left", padx=5)
        
        ctk.CTkLabel(p, text="Features (une par ligne):").pack(anchor="w", pady=(10, 0))
        self.pricing_features = ctk.CTkTextbox(p, height=80)
        self.pricing_features.pack(fill="x", pady=3)
        
        row3 = ctk.CTkFrame(p, fg_color="transparent")
        row3.pack(fill="x", pady=3)
        ctk.CTkLabel(row3, text="Bouton:", width=80).pack(side="left")
        self.pricing_cta = ctk.CTkEntry(row3, width=100, placeholder_text="Choisir")
        self.pricing_cta.pack(side="left", padx=5)
        self.pricing_url = ctk.CTkEntry(row3, placeholder_text="https://...")
        self.pricing_url.pack(side="left", fill="x", expand=True, padx=5)
        
        row4 = ctk.CTkFrame(p, fg_color="transparent")
        row4.pack(fill="x", pady=5)
        self.pricing_highlight = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row4, text="Mise en avant (highlight)", variable=self.pricing_highlight).pack(side="left")
        ctk.CTkLabel(row4, text="Badge:").pack(side="left", padx=(20, 5))
        self.pricing_badge = ctk.CTkEntry(row4, width=100, placeholder_text="Populaire")
        self.pricing_badge.pack(side="left")
        
        c = self.existing_block.content if self.existing_block else {}
        self.pricing_name.insert(0, c.get('name', 'Offre Standard'))
        self.pricing_price.insert(0, c.get('price', '9 900'))
        self.pricing_currency.insert(0, c.get('currency', 'XPF'))
        self.pricing_period.insert(0, c.get('period', '/mois'))
        self.pricing_features.insert("1.0", "\n".join(c.get('features', ['Feature 1', 'Feature 2'])))
        self.pricing_cta.insert(0, c.get('cta_text', 'Choisir'))
        self.pricing_url.insert(0, c.get('cta_url', ''))
        self.pricing_highlight.set(c.get('highlighted', False))
        self.pricing_badge.insert(0, c.get('badge', ''))
    
    def _ui_timeline(self, p):
        ctk.CTkLabel(p, text="📅 Timeline / Étapes", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Étapes (icône | titre | description, une par ligne):").pack(anchor="w")
        self.timeline_items = ctk.CTkTextbox(p, height=150)
        self.timeline_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.timeline_style = ctk.CTkSegmentedButton(row, values=["vertical", "horizontal"], width=180)
        self.timeline_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        items_text = "\n".join(f"{i.get('icon','')} | {i.get('title','')} | {i.get('description','')}" for i in c.get('items', []))
        self.timeline_items.insert("1.0", items_text or "1 | Étape 1 | Description\n2 | Étape 2 | Description\n3 | Étape 3 | Description")
        self.timeline_style.set(c.get('style', 'vertical'))
    
    def _ui_team(self, p):
        ctk.CTkLabel(p, text="👤 Profil Équipe", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=3)
        ctk.CTkLabel(row1, text="Nom:", width=80).pack(side="left")
        self.team_name = ctk.CTkEntry(row1)
        self.team_name.pack(side="left", fill="x", expand=True, padx=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=3)
        ctk.CTkLabel(row2, text="Fonction:", width=80).pack(side="left")
        self.team_title = ctk.CTkEntry(row2)
        self.team_title.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(p, text="Bio:").pack(anchor="w")
        self.team_bio = ctk.CTkTextbox(p, height=60)
        self.team_bio.pack(fill="x", pady=3)
        
        ctk.CTkLabel(p, text="Photo URL:").pack(anchor="w")
        self.team_photo = ctk.CTkEntry(p, placeholder_text="https://...")
        self.team_photo.pack(fill="x", pady=3)
        
        row3 = ctk.CTkFrame(p, fg_color="transparent")
        row3.pack(fill="x", pady=3)
        ctk.CTkLabel(row3, text="Email:", width=80).pack(side="left")
        self.team_email = ctk.CTkEntry(row3, width=150)
        self.team_email.pack(side="left", padx=5)
        ctk.CTkLabel(row3, text="Tél:").pack(side="left")
        self.team_phone = ctk.CTkEntry(row3, width=120)
        self.team_phone.pack(side="left", padx=5)
        
        row4 = ctk.CTkFrame(p, fg_color="transparent")
        row4.pack(fill="x", pady=5)
        ctk.CTkLabel(row4, text="Style:").pack(side="left")
        self.team_style = ctk.CTkSegmentedButton(row4, values=["card", "horizontal", "minimal"], width=200)
        self.team_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.team_name.insert(0, c.get('name', 'Nom Prénom'))
        self.team_title.insert(0, c.get('title', 'Fonction'))
        self.team_bio.insert("1.0", c.get('bio', ''))
        self.team_photo.insert(0, c.get('photo_url', ''))
        self.team_email.insert(0, c.get('email', ''))
        self.team_phone.insert(0, c.get('phone', ''))
        self.team_style.set(c.get('style', 'card'))
    
    def _ui_rating(self, p):
        ctk.CTkLabel(p, text="⭐ Note / Étoiles", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Note:").pack(side="left")
        self.rating_value = ctk.CTkEntry(row1, width=50)
        self.rating_value.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="/").pack(side="left")
        self.rating_max = ctk.CTkEntry(row1, width=50)
        self.rating_max.pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Style:").pack(side="left")
        self.rating_style = ctk.CTkSegmentedButton(row2, values=["stars", "numeric", "both"], width=200)
        self.rating_style.pack(side="left", padx=10)
        
        row3 = ctk.CTkFrame(p, fg_color="transparent")
        row3.pack(fill="x", pady=5)
        ctk.CTkLabel(row3, text="Taille:").pack(side="left")
        self.rating_size = ctk.CTkSegmentedButton(row3, values=["small", "medium", "large"], width=200)
        self.rating_size.pack(side="left", padx=10)
        
        ctk.CTkLabel(p, text="Texte (optionnel):").pack(anchor="w")
        self.rating_text = ctk.CTkEntry(p, placeholder_text="Avis clients")
        self.rating_text.pack(fill="x", pady=3)
        
        c = self.existing_block.content if self.existing_block else {}
        self.rating_value.insert(0, str(c.get('rating', 5)))
        self.rating_max.insert(0, str(c.get('max_rating', 5)))
        self.rating_style.set(c.get('style', 'stars'))
        self.rating_size.set(c.get('size', 'medium'))
        self.rating_text.insert(0, c.get('text', ''))
    
    def _ui_feature_box(self, p):
        ctk.CTkLabel(p, text="✨ Boîtes Features", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Features (icône | titre | description, une par ligne):").pack(anchor="w")
        self.feature_items = ctk.CTkTextbox(p, height=120)
        self.feature_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Colonnes:").pack(side="left")
        self.feature_cols = ctk.CTkSegmentedButton(row, values=["2", "3", "4"], width=120)
        self.feature_cols.pack(side="left", padx=10)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.feature_style = ctk.CTkSegmentedButton(row, values=["cards", "minimal", "icons"], width=180)
        self.feature_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        items_text = "\n".join(f"{f.get('icon','')} | {f.get('title','')} | {f.get('description','')}" for f in c.get('features', []))
        self.feature_items.insert("1.0", items_text or "🚀 | Rapide | Description\n🔒 | Sécurisé | Description\n💡 | Innovant | Description")
        self.feature_cols.set(str(c.get('columns', 3)))
        self.feature_style.set(c.get('style', 'cards'))
    
    def _ui_table(self, p):
        ctk.CTkLabel(p, text="📊 Tableau", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="En-têtes (séparés par |):").pack(anchor="w")
        self.table_headers = ctk.CTkEntry(p)
        self.table_headers.pack(fill="x", pady=3)
        
        ctk.CTkLabel(p, text="Lignes (valeurs séparées par |, une ligne par row):").pack(anchor="w")
        self.table_rows = ctk.CTkTextbox(p, height=100)
        self.table_rows.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.table_style = ctk.CTkSegmentedButton(row, values=["striped", "bordered", "minimal"], width=200)
        self.table_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.table_headers.insert(0, " | ".join(c.get('headers', ['Col 1', 'Col 2', 'Col 3'])))
        rows_text = "\n".join(" | ".join(row) for row in c.get('rows', [['Val 1', 'Val 2', 'Val 3']]))
        self.table_rows.insert("1.0", rows_text)
        self.table_style.set(c.get('style', 'striped'))
    
    def _ui_progress(self, p):
        ctk.CTkLabel(p, text="📶 Barres de Progression", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Items (label | valeur | max, un par ligne):").pack(anchor="w")
        self.progress_items = ctk.CTkTextbox(p, height=100)
        self.progress_items.pack(fill="x", pady=5)
        
        self.progress_show_pct = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(p, text="Afficher pourcentage", variable=self.progress_show_pct).pack(anchor="w", pady=5)
        
        c = self.existing_block.content if self.existing_block else {}
        items_text = "\n".join(f"{i.get('label','')} | {i.get('value',0)} | {i.get('max',100)}" for i in c.get('items', []))
        self.progress_items.insert("1.0", items_text or "Objectif ventes | 75 | 100\nClients satisfaits | 95 | 100")
        self.progress_show_pct.set(c.get('show_percentage', True))
    
    def _ui_separator_text(self, p):
        ctk.CTkLabel(p, text="➖ Séparateur avec Texte", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Texte:").pack(anchor="w")
        self.septext_text = ctk.CTkEntry(p)
        self.septext_text.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.septext_style = ctk.CTkSegmentedButton(row, values=["line", "dots", "gradient"], width=200)
        self.septext_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.septext_text.insert(0, c.get('text', 'ou'))
        self.septext_style.set(c.get('style', 'line'))
    
    def _ui_before_after(self, p):
        ctk.CTkLabel(p, text="🔄 Avant/Après", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Image AVANT (URL):").pack(anchor="w")
        self.ba_before = ctk.CTkEntry(p, placeholder_text="https://...")
        self.ba_before.pack(fill="x", pady=3)
        
        ctk.CTkLabel(p, text="Image APRÈS (URL):").pack(anchor="w")
        self.ba_after = ctk.CTkEntry(p, placeholder_text="https://...")
        self.ba_after.pack(fill="x", pady=3)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Label avant:").pack(side="left")
        self.ba_label1 = ctk.CTkEntry(row, width=100)
        self.ba_label1.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="Label après:").pack(side="left", padx=(15,0))
        self.ba_label2 = ctk.CTkEntry(row, width=100)
        self.ba_label2.pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Style:").pack(side="left")
        self.ba_style = ctk.CTkSegmentedButton(row2, values=["side_by_side", "stacked"], width=200)
        self.ba_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.ba_before.insert(0, c.get('before_image', ''))
        self.ba_after.insert(0, c.get('after_image', ''))
        self.ba_label1.insert(0, c.get('before_label', 'Avant'))
        self.ba_label2.insert(0, c.get('after_label', 'Après'))
        self.ba_style.set(c.get('style', 'side_by_side'))
    
    def _ui_icon_row(self, p):
        ctk.CTkLabel(p, text="🎯 Icônes en ligne", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Items (icône | texte, un par ligne):").pack(anchor="w")
        self.iconrow_items = ctk.CTkTextbox(p, height=100)
        self.iconrow_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.iconrow_style = ctk.CTkSegmentedButton(row, values=["inline", "badges"], width=150)
        self.iconrow_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        items_text = "\n".join(f"{i.get('icon','')} | {i.get('text','')}" for i in c.get('items', []))
        self.iconrow_items.insert("1.0", items_text or "🚚 | Livraison gratuite\n🔒 | Paiement sécurisé\n↩️ | Retour facile")
        self.iconrow_style.set(c.get('style', 'inline'))
    
    def _ui_callout(self, p):
        ctk.CTkLabel(p, text="💡 Callout", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=3)
        ctk.CTkLabel(row1, text="Icône:").pack(side="left")
        self.callout_icon = ctk.CTkEntry(row1, width=60)
        self.callout_icon.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Titre:").pack(side="left", padx=(15,0))
        self.callout_title = ctk.CTkEntry(row1)
        self.callout_title.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(p, text="Texte:").pack(anchor="w")
        self.callout_text = ctk.CTkTextbox(p, height=80)
        self.callout_text.pack(fill="x", pady=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Type:").pack(side="left")
        self.callout_style = ctk.CTkSegmentedButton(row2, values=["tip", "warning", "success", "info", "quote"], width=280)
        self.callout_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.callout_icon.insert(0, c.get('icon', '💡'))
        self.callout_title.insert(0, c.get('title', 'Le saviez-vous ?'))
        self.callout_text.insert("1.0", c.get('text', ''))
        self.callout_style.set(c.get('style', 'tip'))
    
    def _ui_checklist(self, p):
        ctk.CTkLabel(p, text="☑️ Checklist", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Titre (optionnel):").pack(anchor="w")
        self.checklist_title = ctk.CTkEntry(p)
        self.checklist_title.pack(fill="x", pady=3)
        
        ctk.CTkLabel(p, text="Items (✓ ou ✗ | texte, un par ligne):").pack(anchor="w")
        self.checklist_items = ctk.CTkTextbox(p, height=120)
        self.checklist_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.checklist_style = ctk.CTkSegmentedButton(row, values=["modern", "simple", "strikethrough"], width=220)
        self.checklist_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.checklist_title.insert(0, c.get('title', ''))
        items_text = "\n".join(f"{'✓' if i.get('checked') else '✗'} | {i.get('text','')}" for i in c.get('items', []))
        self.checklist_items.insert("1.0", items_text or "✓ | Élément complété\n✓ | Autre élément\n✗ | À faire")
        self.checklist_style.set(c.get('style', 'modern'))
    
    def _ui_contact(self, p):
        ctk.CTkLabel(p, text="📞 Bloc Contact", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        fields = [("Titre:", "contact_title", "Contactez-nous"),
                  ("Email:", "contact_email", COMPANY_EMAIL),
                  ("Téléphone:", "contact_phone", COMPANY_PHONE),
                  ("Adresse:", "contact_address", COMPANY_ADDRESS),
                  ("Site web:", "contact_website", COMPANY_WEBSITE),
                  ("Horaires:", "contact_hours", "Lun-Ven: 8h-17h")]
        
        self.contact_entries = {}
        for label, key, default in fields:
            row = ctk.CTkFrame(p, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, width=80).pack(side="left")
            entry = ctk.CTkEntry(row)
            entry.pack(side="left", fill="x", expand=True, padx=5)
            entry.insert(0, default)
            self.contact_entries[key] = entry
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.contact_style = ctk.CTkSegmentedButton(row, values=["card", "inline", "minimal"], width=200)
        self.contact_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        for key, entry in self.contact_entries.items():
            field = key.replace("contact_", "")
            if c.get(field): entry.delete(0, "end"); entry.insert(0, c.get(field))
        self.contact_style.set(c.get('style', 'card'))
    
    def _ui_banner(self, p):
        ctk.CTkLabel(p, text="🎪 Bannière", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Texte principal:").pack(anchor="w")
        self.banner_text = ctk.CTkEntry(p)
        self.banner_text.pack(fill="x", pady=3)
        
        ctk.CTkLabel(p, text="Sous-texte:").pack(anchor="w")
        self.banner_subtext = ctk.CTkEntry(p)
        self.banner_subtext.pack(fill="x", pady=3)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Style:").pack(side="left")
        self.banner_style = ctk.CTkSegmentedButton(row1, values=["gradient", "solid", "outline"], width=200)
        self.banner_style.pack(side="left", padx=10)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Taille:").pack(side="left")
        self.banner_size = ctk.CTkSegmentedButton(row2, values=["small", "medium", "large"], width=200)
        self.banner_size.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.banner_text.insert(0, c.get('text', '🎉 Offre spéciale !'))
        self.banner_subtext.insert(0, c.get('subtext', ''))
        self.banner_style.set(c.get('style', 'gradient'))
        self.banner_size.set(c.get('size', 'medium'))
    
    def _ui_avatar_group(self, p):
        ctk.CTkLabel(p, text="👥 Groupe d'avatars", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Avatars (nom | url_image, un par ligne):").pack(anchor="w")
        self.avatar_items = ctk.CTkTextbox(p, height=100)
        self.avatar_items.pack(fill="x", pady=5)
        
        ctk.CTkLabel(p, text="Texte accompagnant:").pack(anchor="w")
        self.avatar_text = ctk.CTkEntry(p, placeholder_text="+500 clients satisfaits")
        self.avatar_text.pack(fill="x", pady=3)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.avatar_style = ctk.CTkSegmentedButton(row, values=["overlap", "grid", "list"], width=180)
        self.avatar_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        items_text = "\n".join(f"{a.get('name','')} | {a.get('image','')}" for a in c.get('avatars', []))
        self.avatar_items.insert("1.0", items_text or "Alice |\nBob |\nCharlie |")
        self.avatar_text.insert(0, c.get('text', '+500 clients satisfaits'))
        self.avatar_style.set(c.get('style', 'overlap'))
    
    def _ui_gradient_text(self, p):
        ctk.CTkLabel(p, text="🌈 Texte Dégradé", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Texte:").pack(anchor="w")
        self.gradtext_text = ctk.CTkEntry(p)
        self.gradtext_text.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Taille:").pack(side="left")
        self.gradtext_size = ctk.CTkEntry(row1, width=60)
        self.gradtext_size.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Alignement:").pack(side="left", padx=(15,0))
        self.gradtext_align = ctk.CTkSegmentedButton(row1, values=["left", "center", "right"], width=180)
        self.gradtext_align.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.gradtext_text.insert(0, c.get('text', 'Texte Stylisé'))
        self.gradtext_size.insert(0, str(c.get('font_size', 36)))
        self.gradtext_align.set(c.get('align', 'center'))
    
    def _ui_logo_cloud(self, p):
        ctk.CTkLabel(p, text="🏢 Logos Partenaires", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Titre:").pack(anchor="w")
        self.logocloud_title = ctk.CTkEntry(p, placeholder_text="Ils nous font confiance")
        self.logocloud_title.pack(fill="x", pady=3)
        
        ctk.CTkLabel(p, text="Logos (nom | url_image, un par ligne):").pack(anchor="w")
        self.logocloud_items = ctk.CTkTextbox(p, height=100)
        self.logocloud_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Colonnes:").pack(side="left")
        self.logocloud_cols = ctk.CTkSegmentedButton(row, values=["2", "3", "4", "5"], width=160)
        self.logocloud_cols.pack(side="left", padx=10)
        
        self.logocloud_gray = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(p, text="Logos en niveaux de gris", variable=self.logocloud_gray).pack(anchor="w", pady=5)
        
        c = self.existing_block.content if self.existing_block else {}
        self.logocloud_title.insert(0, c.get('title', 'Ils nous font confiance'))
        items_text = "\n".join(f"{l.get('name','')} | {l.get('url','')}" for l in c.get('logos', []))
        self.logocloud_items.insert("1.0", items_text or "Partenaire 1 |\nPartenaire 2 |\nPartenaire 3 |")
        self.logocloud_cols.set(str(c.get('columns', 3)))
        self.logocloud_gray.set(c.get('grayscale', True))
    
    def _ui_number_highlight(self, p):
        ctk.CTkLabel(p, text="🔢 Chiffre Clé", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Préfixe:").pack(side="left")
        self.numhl_prefix = ctk.CTkEntry(row1, width=50)
        self.numhl_prefix.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Nombre:").pack(side="left")
        self.numhl_number = ctk.CTkEntry(row1, width=100)
        self.numhl_number.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Suffixe:").pack(side="left")
        self.numhl_suffix = ctk.CTkEntry(row1, width=50)
        self.numhl_suffix.pack(side="left", padx=5)
        
        ctk.CTkLabel(p, text="Label:").pack(anchor="w")
        self.numhl_label = ctk.CTkEntry(p)
        self.numhl_label.pack(fill="x", pady=3)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Style:").pack(side="left")
        self.numhl_style = ctk.CTkSegmentedButton(row2, values=["gradient", "solid", "outline"], width=200)
        self.numhl_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.numhl_prefix.insert(0, c.get('prefix', ''))
        self.numhl_number.insert(0, c.get('number', '100'))
        self.numhl_suffix.insert(0, c.get('suffix', '+'))
        self.numhl_label.insert(0, c.get('label', 'Clients satisfaits'))
        self.numhl_style.set(c.get('style', 'gradient'))
    
    def _ui_divider_icon(self, p):
        ctk.CTkLabel(p, text="✦ Séparateur avec Icône", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="Icône:").pack(side="left")
        self.divicon_icon = ctk.CTkEntry(row1, width=60)
        self.divicon_icon.pack(side="left", padx=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Style ligne:").pack(side="left")
        self.divicon_style = ctk.CTkSegmentedButton(row2, values=["solid", "dashed", "dots"], width=180)
        self.divicon_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.divicon_icon.insert(0, c.get('icon', '✦'))
        self.divicon_style.set(c.get('line_style', 'solid'))
    
    def _ui_qr_code(self, p):
        ctk.CTkLabel(p, text="📱 QR Code", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="URL à encoder:").pack(anchor="w")
        self.qr_url = ctk.CTkEntry(p, placeholder_text="https://...")
        self.qr_url.pack(fill="x", pady=3)
        
        ctk.CTkLabel(p, text="Label (optionnel):").pack(anchor="w")
        self.qr_label = ctk.CTkEntry(p, placeholder_text="Scannez pour accéder")
        self.qr_label.pack(fill="x", pady=3)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Taille:").pack(side="left")
        self.qr_size = ctk.CTkEntry(row, width=60)
        self.qr_size.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="Alignement:").pack(side="left", padx=(15,0))
        self.qr_style = ctk.CTkSegmentedButton(row, values=["centered", "left", "right"], width=180)
        self.qr_style.pack(side="left", padx=10)
        
        # Bouton pour tester le QR code
        def test_qr():
            url = self.qr_url.get() or f"https://{COMPANY_WEBSITE}"
            if not url.startswith('http'):
                url = 'https://' + url
            size = self.qr_size.get() or "150"
            encoded = urllib.parse.quote_plus(url)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded}&format=png"
            webbrowser.open(qr_url)
        
        ctk.CTkButton(p, text="🔍 Tester le QR Code", fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK,
                      command=test_qr).pack(pady=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.qr_url.insert(0, c.get('url', f'https://{COMPANY_WEBSITE}'))
        self.qr_label.insert(0, c.get('label', 'Scannez pour accéder'))
        self.qr_size.insert(0, str(c.get('size', 150)))
        self.qr_style.set(c.get('style', 'centered'))
    
    def _ui_faq(self, p):
        ctk.CTkLabel(p, text="❓ FAQ", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Titre (optionnel):").pack(anchor="w")
        self.faq_title = ctk.CTkEntry(p)
        self.faq_title.pack(fill="x", pady=3)
        
        ctk.CTkLabel(p, text="Questions/Réponses (Q: ... | R: ..., une par ligne):").pack(anchor="w")
        self.faq_items = ctk.CTkTextbox(p, height=150)
        self.faq_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.faq_style = ctk.CTkSegmentedButton(row, values=["cards", "simple", "numbered"], width=200)
        self.faq_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.faq_title.insert(0, c.get('title', 'Questions fréquentes'))
        items_text = "\n".join(f"Q: {i.get('question','')} | R: {i.get('answer','')}" for i in c.get('items', []))
        self.faq_items.insert("1.0", items_text or "Q: Question 1 ? | R: Réponse 1.\nQ: Question 2 ? | R: Réponse 2.")
        self.faq_style.set(c.get('style', 'cards'))
    
    def _ui_comparison(self, p):
        ctk.CTkLabel(p, text="⚖️ Comparaison", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Titre (optionnel):").pack(anchor="w")
        self.comp_title = ctk.CTkEntry(p)
        self.comp_title.pack(fill="x", pady=3)
        
        # Option 1
        ctk.CTkLabel(p, text="Option 1:", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(10, 3))
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x")
        ctk.CTkLabel(row1, text="Nom:").pack(side="left")
        self.comp_name1 = ctk.CTkEntry(row1, width=150)
        self.comp_name1.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Prix:").pack(side="left", padx=(10,0))
        self.comp_price1 = ctk.CTkEntry(row1, width=100)
        self.comp_price1.pack(side="left", padx=5)
        
        ctk.CTkLabel(p, text="Features (une par ligne):").pack(anchor="w")
        self.comp_feat1 = ctk.CTkTextbox(p, height=60)
        self.comp_feat1.pack(fill="x", pady=3)
        
        # Option 2
        ctk.CTkLabel(p, text="Option 2:", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(10, 3))
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x")
        ctk.CTkLabel(row2, text="Nom:").pack(side="left")
        self.comp_name2 = ctk.CTkEntry(row2, width=150)
        self.comp_name2.pack(side="left", padx=5)
        ctk.CTkLabel(row2, text="Prix:").pack(side="left", padx=(10,0))
        self.comp_price2 = ctk.CTkEntry(row2, width=100)
        self.comp_price2.pack(side="left", padx=5)
        self.comp_hl2 = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row2, text="Recommandé", variable=self.comp_hl2).pack(side="left", padx=10)
        
        ctk.CTkLabel(p, text="Features (une par ligne):").pack(anchor="w")
        self.comp_feat2 = ctk.CTkTextbox(p, height=60)
        self.comp_feat2.pack(fill="x", pady=3)
        
        c = self.existing_block.content if self.existing_block else {}
        self.comp_title.insert(0, c.get('title', ''))
        opt1 = c.get('option_1', {})
        opt2 = c.get('option_2', {})
        self.comp_name1.insert(0, opt1.get('name', 'Option A'))
        self.comp_price1.insert(0, opt1.get('price', ''))
        self.comp_feat1.insert("1.0", "\n".join(opt1.get('features', ['Feature 1', 'Feature 2'])))
        self.comp_name2.insert(0, opt2.get('name', 'Option B'))
        self.comp_price2.insert(0, opt2.get('price', ''))
        self.comp_feat2.insert("1.0", "\n".join(opt2.get('features', ['Feature 1', 'Feature 2', 'Feature 3'])))
        self.comp_hl2.set(opt2.get('highlight', True))
    
    def _ui_coupon(self, p):
        ctk.CTkLabel(p, text="🎟️ Coupon", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        fields = [("Titre:", "coupon_title", "BON DE RÉDUCTION"),
                  ("Valeur:", "coupon_value", "-20%"),
                  ("Description:", "coupon_desc", "Sur votre prochain achat"),
                  ("Code:", "coupon_code", "PROMO20"),
                  ("Validité:", "coupon_expiry", "Valable jusqu'au 31/12/2025")]
        
        self.coupon_entries = {}
        for label, key, default in fields:
            row = ctk.CTkFrame(p, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, width=80).pack(side="left")
            entry = ctk.CTkEntry(row)
            entry.pack(side="left", fill="x", expand=True, padx=5)
            entry.insert(0, default)
            self.coupon_entries[key] = entry
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.coupon_style = ctk.CTkSegmentedButton(row, values=["ticket", "simple", "premium"], width=200)
        self.coupon_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        if c:
            self.coupon_entries['coupon_title'].delete(0, "end"); self.coupon_entries['coupon_title'].insert(0, c.get('title', 'BON DE RÉDUCTION'))
            self.coupon_entries['coupon_value'].delete(0, "end"); self.coupon_entries['coupon_value'].insert(0, c.get('value', '-20%'))
            self.coupon_entries['coupon_desc'].delete(0, "end"); self.coupon_entries['coupon_desc'].insert(0, c.get('description', ''))
            self.coupon_entries['coupon_code'].delete(0, "end"); self.coupon_entries['coupon_code'].insert(0, c.get('code', 'PROMO20'))
            self.coupon_entries['coupon_expiry'].delete(0, "end"); self.coupon_entries['coupon_expiry'].insert(0, c.get('expiry', ''))
        self.coupon_style.set(c.get('style', 'ticket'))
    
    def _ui_steps(self, p):
        ctk.CTkLabel(p, text="1️⃣ Étapes", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ctk.CTkLabel(p, text="Titre (optionnel):").pack(anchor="w")
        self.steps_title = ctk.CTkEntry(p)
        self.steps_title.pack(fill="x", pady=3)
        
        ctk.CTkLabel(p, text="Étapes (titre | description, une par ligne):").pack(anchor="w")
        self.steps_items = ctk.CTkTextbox(p, height=120)
        self.steps_items.pack(fill="x", pady=5)
        
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", pady=5)
        ctk.CTkLabel(row, text="Style:").pack(side="left")
        self.steps_style = ctk.CTkSegmentedButton(row, values=["numbered", "circles", "icons"], width=200)
        self.steps_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.steps_title.insert(0, c.get('title', ''))
        items_text = "\n".join(f"{s.get('title','')} | {s.get('description','')}" for s in c.get('steps', []))
        self.steps_items.insert("1.0", items_text or "Étape 1 | Description de l'étape 1\nÉtape 2 | Description de l'étape 2\nÉtape 3 | Description de l'étape 3")
        self.steps_style.set(c.get('style', 'numbered'))
    
    def _ui_highlight_box(self, p):
        ctk.CTkLabel(p, text="🔥 Box Vedette", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", pady=3)
        ctk.CTkLabel(row1, text="Icône:").pack(side="left")
        self.hlbox_icon = ctk.CTkEntry(row1, width=60)
        self.hlbox_icon.pack(side="left", padx=5)
        ctk.CTkLabel(row1, text="Titre:").pack(side="left", padx=(15,0))
        self.hlbox_title = ctk.CTkEntry(row1)
        self.hlbox_title.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(p, text="Texte:").pack(anchor="w")
        self.hlbox_text = ctk.CTkTextbox(p, height=80)
        self.hlbox_text.pack(fill="x", pady=5)
        
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="Style:").pack(side="left")
        self.hlbox_style = ctk.CTkSegmentedButton(row2, values=["gradient", "neon", "bordered", "minimal"], width=260)
        self.hlbox_style.pack(side="left", padx=10)
        
        c = self.existing_block.content if self.existing_block else {}
        self.hlbox_icon.insert(0, c.get('icon', '🔥'))
        self.hlbox_title.insert(0, c.get('title', 'Important !'))
        self.hlbox_text.insert("1.0", c.get('text', ''))
        self.hlbox_style.set(c.get('style', 'gradient'))
    
    def _set_val(self, entry, val):
        entry.delete(0, "end")
        entry.insert(0, str(val))
    
    def _pick_color(self, attr):
        btn = getattr(self, attr, None)
        if not btn: return
        dialog = ColorPickerDialog(self, btn.cget("fg_color") or "#888")
        self.wait_window(dialog)
        if dialog.result: btn.configure(fg_color=dialog.result)
    
    def _save(self):
        try:
            if self.block_type == "text":
                self.result = TextBlock({
                    "text": self.text_content.get("1.0", "end-1c"), "font_size": int(self.font_size.get() or 15),
                    "color": self.text_color_btn.cget("fg_color"), "background": self.bg_color_btn.cget("fg_color"),
                    "bold": self.bold_var.get(), "italic": self.italic_var.get(), "underline": self.underline_var.get(),
                    "align": self.align.get(), "font_family": "Segoe UI, sans-serif", "line_height": 1.8,
                    "padding": {"top": 10, "right": 0, "bottom": 10, "left": 0},
                    "margin": {"top": 0, "right": 0, "bottom": 0, "left": 0}, "border_radius": 0})
            elif self.block_type == "title":
                self.result = TitleBlock({
                    "text": self.title_text.get(), "level": self.title_level.get(),
                    "font_size": int(self.title_size.get() or 24), "font_family": "Segoe UI, sans-serif",
                    "color": KRYSTO_DARK, "align": self.title_align.get(),
                    "underline_style": self.underline_style.get(), "underline_color": KRYSTO_SECONDARY,
                    "underline_height": 3, "margin_bottom": 20})
            elif self.block_type == "image":
                self.result = ImageBlock({
                    "url": self.image_url.get(), "alt": "Image", "width": self.image_width.get() or "100%",
                    "max_width": "100%", "height": "auto", "align": self.image_align.get(),
                    "border_radius": int(self.image_radius.get() or 12), "shadow": self.image_shadow.get(),
                    "caption": self.image_caption.get(), "caption_color": "#666666",
                    "link_url": self.image_link.get(), "padding": 10})
            elif self.block_type == "button":
                self.result = ButtonBlock({
                    "text": self.btn_text.get(), "url": self.btn_url.get() or f"https://{COMPANY_WEBSITE}",
                    "style": self.btn_style.get(), "bg_color": KRYSTO_PRIMARY, "bg_color_2": KRYSTO_SECONDARY,
                    "text_color": "#ffffff", "border_color": KRYSTO_PRIMARY, "font_size": 15,
                    "padding_x": 40, "padding_y": 14, "border_radius": 25, "shadow": self.btn_shadow.get(),
                    "icon": self.btn_icon.get(), "icon_position": "left",
                    "full_width": self.btn_full_width.get(), "align": self.btn_align.get()})
            elif self.block_type == "divider":
                self.result = DividerBlock({
                    "style": self.divider_style.get(), "color": self.divider_color.cget("fg_color"),
                    "color_2": KRYSTO_PRIMARY, "height": int(self.divider_height.get() or 3),
                    "width": "100%", "align": "center", "margin_top": 20, "margin_bottom": 20, "border_radius": 2})
            elif self.block_type == "spacer":
                self.result = SpacerBlock({"height": int(self.spacer_height.get() or 30)})
            elif self.block_type == "quote":
                self.result = QuoteBlock({
                    "text": self.quote_text.get("1.0", "end-1c"), "author": self.quote_author.get(),
                    "style": self.quote_style.get(), "accent_color": KRYSTO_PRIMARY, "bg_color": "#f8f9fa",
                    "text_color": KRYSTO_DARK, "font_size": 16, "font_style": "italic", "padding": 25, "border_radius": 12})
            elif self.block_type == "list":
                items = []
                for line in self.list_items.get("1.0", "end-1c").split("\n"):
                    line = line.strip()
                    if not line: continue
                    parts = line.split("|")
                    if len(parts) >= 2: items.append({"icon": parts[0].strip(), "text": parts[1].strip()})
                    else: items.append({"icon": "✓", "text": line})
                self.result = ListBlock({
                    "items": items, "style": self.list_style.get(), "default_icon": "✓",
                    "icon_color": KRYSTO_SECONDARY, "text_color": KRYSTO_DARK, "font_size": 14, "spacing": 12, "icon_size": 18})
            elif self.block_type == "promo_code":
                self.result = PromoCodeBlock({
                    "code": self.promo_code.get(), "description": self.promo_desc.get(),
                    "expiry": self.promo_expiry.get(), "style": self.promo_style.get(),
                    "gradient_start": KRYSTO_PRIMARY, "gradient_end": KRYSTO_SECONDARY, "text_color": "#ffffff"})
            elif self.block_type == "social":
                # Nouveau format: dictionnaire avec URLs
                networks = {net_id: entry.get().strip() for net_id, entry in self.social_entries.items()}
                self.result = SocialBlock({
                    "networks": networks, 
                    "style": self.social_style.get(), 
                    "size": int(self.social_size.get() or 40), 
                    "gap": 12,
                    "align": "center", 
                    "border_radius": 50,
                    "mono_color": "#666666"
                })
            elif self.block_type == "html":
                self.result = HtmlBlock({"html": self.html_content.get("1.0", "end-1c")})
            
            elif self.block_type == "image_grid":
                images = []
                for line in self.grid_images.get("1.0", "end-1c").split("\n"):
                    if not line.strip(): continue
                    parts = [p.strip() for p in line.split("|")]
                    images.append({"url": parts[0] if len(parts) > 0 else "",
                                   "caption": parts[1] if len(parts) > 1 else "",
                                   "link": parts[2] if len(parts) > 2 else ""})
                self.result = ImageGridBlock({"images": images, "columns": int(self.grid_cols.get()),
                    "gap": int(self.grid_gap.get() or 15), "border_radius": 12,
                    "shadow": self.grid_shadow.get(), "captions": self.grid_captions.get(),
                    "caption_style": "overlay", "padding": 10})
            
            elif self.block_type == "hero":
                btn_parts = self.hero_btn.get().split("|")
                self.result = HeroBlock({"image_url": self.hero_image.get(),
                    "height": int(self.hero_height.get() or 400), "overlay": True,
                    "title": self.hero_title.get(), "subtitle": self.hero_subtitle.get("1.0", "end-1c"),
                    "text_align": self.hero_align.get(), "text_valign": "center",
                    "button_text": btn_parts[0].strip() if len(btn_parts) > 0 else "",
                    "button_url": btn_parts[1].strip() if len(btn_parts) > 1 else "", "padding": 40})
            
            elif self.block_type == "card":
                btn_parts = self.card_btn.get().split("|")
                self.result = CardBlock({"image_url": self.card_image.get(),
                    "image_position": self.card_img_pos.get(), "title": self.card_title.get(),
                    "description": self.card_desc.get("1.0", "end-1c"),
                    "button_text": btn_parts[0].strip() if len(btn_parts) > 0 else "",
                    "button_url": btn_parts[1].strip() if len(btn_parts) > 1 else "",
                    "shadow": self.card_shadow.get(), "border_radius": 15, "padding": 25})
            
            elif self.block_type == "columns":
                ratio = self.col_ratio.get()
                widths = {"50/50": ("50%", "50%"), "40/60": ("40%", "60%"), 
                          "60/40": ("60%", "40%"), "30/70": ("30%", "70%")}
                w1, w2 = widths.get(ratio, ("50%", "50%"))
                self.result = ColumnsBlock({"columns": [
                    {"width": w1, "content": self.col1_content.get("1.0", "end-1c"), "align": "left", "valign": "top", "padding": 15, "bg_color": "transparent"},
                    {"width": w2, "content": self.col2_content.get("1.0", "end-1c"), "align": "left", "valign": "top", "padding": 15, "bg_color": "transparent"}
                ], "gap": 20})
            
            elif self.block_type == "product":
                self.result = ProductBlock({"image_url": self.prod_image.get(),
                    "name": self.prod_name.get(), "description": self.prod_desc.get("1.0", "end-1c"),
                    "price": self.prod_price.get(), "old_price": self.prod_old_price.get(),
                    "badge": self.prod_badge.get(), "cta_url": self.prod_cta.get(),
                    "cta_text": "Commander", "layout": "horizontal", "border_radius": 12, "shadow": True})
            
            elif self.block_type == "testimonial":
                self.result = TestimonialBlock({"quote": self.testi_quote.get("1.0", "end-1c"),
                    "author_name": self.testi_name.get(), "author_title": self.testi_title.get(),
                    "author_image": self.testi_photo.get(), "rating": int(self.testi_stars.get()),
                    "show_stars": True, "style": "card", "border_radius": 15})
            
            elif self.block_type == "video":
                self.result = VideoBlock({"thumbnail_url": self.video_thumb.get(),
                    "video_url": self.video_url.get(), "title": self.video_title.get(),
                    "duration": self.video_duration.get(), "border_radius": 12, "shadow": True})
            
            elif self.block_type == "countdown":
                self.result = CountdownBlock({"title": self.countdown_title.get(),
                    "days": self.countdown_days.get(), "hours": self.countdown_hours.get(),
                    "minutes": self.countdown_mins.get(), "style": "boxes"})
            
            elif self.block_type == "gallery":
                images = []
                for line in self.gallery_images.get("1.0", "end-1c").split("\n"):
                    if not line.strip(): continue
                    parts = [p.strip() for p in line.split("|")]
                    images.append({"url": parts[0] if len(parts) > 0 else "",
                                   "link": parts[1] if len(parts) > 1 else ""})
                self.result = GalleryBlock({"images": images, "caption": self.gallery_caption.get(),
                    "main_height": int(self.gallery_height.get() or 350), "thumb_size": 80,
                    "gap": 10, "border_radius": 12, "shadow": True})
            
            elif self.block_type == "accordion":
                items = []
                text = self.accordion_items.get("1.0", "end-1c")
                current_q, current_a = "", ""
                for line in text.split("\n"):
                    if line.startswith("Q:"):
                        if current_q: items.append({"question": current_q, "answer": current_a.strip()})
                        current_q = line[2:].strip()
                        current_a = ""
                    elif line.startswith("R:"):
                        current_a = line[2:].strip()
                    else:
                        current_a += " " + line.strip()
                if current_q: items.append({"question": current_q, "answer": current_a.strip()})
                self.result = AccordionBlock({"items": items, "style": self.accordion_style.get()})
            
            elif self.block_type == "stats":
                stats = []
                for line in self.stats_items.get("1.0", "end-1c").split("\n"):
                    if not line.strip(): continue
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2: stats.append({"value": parts[0], "label": parts[1]})
                self.result = StatsBlock({"stats": stats, "columns": int(self.stats_cols.get()),
                    "style": self.stats_style.get()})
            
            elif self.block_type == "map":
                self.result = MapBlock({
                    "address": self.map_address.get(),
                    "image_url": self.map_image.get().strip(),
                    "api_key": self.map_api_key.get().strip(),
                    "zoom": int(self.map_zoom.get() or 15),
                    "map_type": self.map_type.get(),
                    "show_address": self.map_show_address.get(),
                    "height": 250, 
                    "border_radius": 12,
                    "marker_color": "red"
                })
            
            elif self.block_type == "footer_links":
                links = []
                for line in self.footer_links_items.get("1.0", "end-1c").split("\n"):
                    if not line.strip(): continue
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2: links.append({"text": parts[0], "url": parts[1]})
                self.result = FooterLinksBlock({"links": links, "separator": self.footer_sep.get(),
                    "align": self.footer_align.get(), "color": "#888888", "font_size": 13})
            
            elif self.block_type == "unsubscribe":
                self.result = UnsubscribeBlock({
                    "text": self.unsub_text.get(),
                    "admin_email": self.unsub_email.get(),
                    "style": self.unsub_style.get(),
                    "show_info": self.unsub_show_info.get(),
                    "info_text": self.unsub_info.get(),
                    "color": "#888888",
                    "font_size": 12
                })
            
            elif self.block_type == "signature":
                self.result = SignatureBlock({
                    "name": self.sig_name.get(),
                    "title": self.sig_title.get(),
                    "company": self.sig_company.get(),
                    "phone": self.sig_phone.get(),
                    "email": self.sig_email.get(),
                    "website": self.sig_website.get(),
                    "photo_url": self.sig_photo.get(),
                    "style": self.sig_style.get(),
                    "accent_color": KRYSTO_PRIMARY
                })
            
            elif self.block_type == "alert":
                self.result = AlertBlock({
                    "text": self.alert_text.get(),
                    "type": self.alert_type.get(),
                    "style": self.alert_style.get(),
                    "icon": self.alert_icon.get() or "auto"
                })
            
            elif self.block_type == "pricing":
                features = [f.strip() for f in self.pricing_features.get("1.0", "end-1c").split("\n") if f.strip()]
                self.result = PricingBlock({
                    "name": self.pricing_name.get(),
                    "price": self.pricing_price.get(),
                    "currency": self.pricing_currency.get() or "XPF",
                    "period": self.pricing_period.get(),
                    "features": features,
                    "cta_text": self.pricing_cta.get(),
                    "cta_url": self.pricing_url.get(),
                    "highlighted": self.pricing_highlight.get(),
                    "badge": self.pricing_badge.get()
                })
            
            elif self.block_type == "timeline":
                items = []
                for line in self.timeline_items.get("1.0", "end-1c").split("\n"):
                    if not line.strip(): continue
                    parts = [p.strip() for p in line.split("|")]
                    items.append({
                        "icon": parts[0] if len(parts) > 0 else "",
                        "title": parts[1] if len(parts) > 1 else "",
                        "description": parts[2] if len(parts) > 2 else ""
                    })
                self.result = TimelineBlock({
                    "items": items,
                    "style": self.timeline_style.get(),
                    "accent_color": KRYSTO_PRIMARY
                })
            
            elif self.block_type == "team":
                self.result = TeamBlock({
                    "name": self.team_name.get(),
                    "title": self.team_title.get(),
                    "bio": self.team_bio.get("1.0", "end-1c"),
                    "photo_url": self.team_photo.get(),
                    "email": self.team_email.get(),
                    "phone": self.team_phone.get(),
                    "style": self.team_style.get()
                })
            
            elif self.block_type == "rating":
                self.result = RatingBlock({
                    "rating": int(self.rating_value.get() or 5),
                    "max_rating": int(self.rating_max.get() or 5),
                    "style": self.rating_style.get(),
                    "size": self.rating_size.get(),
                    "text": self.rating_text.get(),
                    "color": "#ffc107"
                })
            
            elif self.block_type == "feature_box":
                features = []
                for line in self.feature_items.get("1.0", "end-1c").split("\n"):
                    if not line.strip(): continue
                    parts = [p.strip() for p in line.split("|")]
                    features.append({
                        "icon": parts[0] if len(parts) > 0 else "✨",
                        "title": parts[1] if len(parts) > 1 else "",
                        "description": parts[2] if len(parts) > 2 else ""
                    })
                self.result = FeatureBoxBlock({
                    "features": features,
                    "columns": int(self.feature_cols.get()),
                    "style": self.feature_style.get()
                })
            
            elif self.block_type == "table":
                headers = [h.strip() for h in self.table_headers.get().split("|")]
                rows = []
                for line in self.table_rows.get("1.0", "end-1c").split("\n"):
                    if not line.strip(): continue
                    rows.append([c.strip() for c in line.split("|")])
                self.result = TableBlock({
                    "headers": headers,
                    "rows": rows,
                    "style": self.table_style.get(),
                    "header_bg": KRYSTO_PRIMARY,
                    "header_color": "#ffffff"
                })
            
            elif self.block_type == "progress":
                items = []
                for line in self.progress_items.get("1.0", "end-1c").split("\n"):
                    if not line.strip(): continue
                    parts = [p.strip() for p in line.split("|")]
                    items.append({
                        "label": parts[0] if len(parts) > 0 else "",
                        "value": int(parts[1]) if len(parts) > 1 else 0,
                        "max": int(parts[2]) if len(parts) > 2 else 100
                    })
                self.result = ProgressBlock({
                    "items": items,
                    "show_percentage": self.progress_show_pct.get(),
                    "color": KRYSTO_PRIMARY
                })
            
            elif self.block_type == "separator_text":
                self.result = SeparatorTextBlock({
                    "text": self.septext_text.get(),
                    "style": self.septext_style.get(),
                    "color": "#e0e0e0",
                    "text_color": "#888888"
                })
            
            elif self.block_type == "before_after":
                self.result = BeforeAfterBlock({
                    "before_image": self.ba_before.get(),
                    "after_image": self.ba_after.get(),
                    "before_label": self.ba_label1.get(),
                    "after_label": self.ba_label2.get(),
                    "style": self.ba_style.get(),
                    "border_radius": 12
                })
            
            elif self.block_type == "icon_row":
                items = []
                for line in self.iconrow_items.get("1.0", "end-1c").strip().split("\n"):
                    if "|" in line:
                        parts = line.split("|", 1)
                        items.append({"icon": parts[0].strip(), "text": parts[1].strip()})
                self.result = IconRowBlock({
                    "items": items,
                    "style": self.iconrow_style.get(),
                    "icon_size": 24,
                    "color": KRYSTO_PRIMARY
                })
            
            elif self.block_type == "callout":
                self.result = CalloutBlock({
                    "icon": self.callout_icon.get(),
                    "title": self.callout_title.get(),
                    "text": self.callout_text.get("1.0", "end-1c"),
                    "style": self.callout_style.get(),
                    "show_icon": True
                })
            
            elif self.block_type == "checklist":
                items = []
                for line in self.checklist_items.get("1.0", "end-1c").strip().split("\n"):
                    if "|" in line:
                        parts = line.split("|", 1)
                        checked = "✓" in parts[0] or "✔" in parts[0]
                        items.append({"text": parts[1].strip(), "checked": checked})
                self.result = ChecklistBlock({
                    "title": self.checklist_title.get(),
                    "items": items,
                    "style": self.checklist_style.get(),
                    "checked_color": KRYSTO_SECONDARY,
                    "unchecked_color": "#ccc"
                })
            
            elif self.block_type == "contact":
                self.result = ContactBlock({
                    "title": self.contact_entries['contact_title'].get(),
                    "email": self.contact_entries['contact_email'].get(),
                    "phone": self.contact_entries['contact_phone'].get(),
                    "address": self.contact_entries['contact_address'].get(),
                    "website": self.contact_entries['contact_website'].get(),
                    "hours": self.contact_entries['contact_hours'].get(),
                    "style": self.contact_style.get(),
                    "show_icons": True
                })
            
            elif self.block_type == "banner":
                self.result = BannerBlock({
                    "text": self.banner_text.get(),
                    "subtext": self.banner_subtext.get(),
                    "style": self.banner_style.get(),
                    "color_1": KRYSTO_PRIMARY,
                    "color_2": KRYSTO_SECONDARY,
                    "text_color": "#ffffff",
                    "size": self.banner_size.get()
                })
            
            elif self.block_type == "avatar_group":
                avatars = []
                for line in self.avatar_items.get("1.0", "end-1c").strip().split("\n"):
                    if "|" in line:
                        parts = line.split("|", 1)
                        avatars.append({"name": parts[0].strip(), "image": parts[1].strip()})
                self.result = AvatarGroupBlock({
                    "avatars": avatars,
                    "text": self.avatar_text.get(),
                    "style": self.avatar_style.get(),
                    "size": 50
                })
            
            elif self.block_type == "gradient_text":
                self.result = GradientTextBlock({
                    "text": self.gradtext_text.get(),
                    "color_1": KRYSTO_PRIMARY,
                    "color_2": KRYSTO_SECONDARY,
                    "font_size": int(self.gradtext_size.get() or 36),
                    "font_weight": "bold",
                    "align": self.gradtext_align.get()
                })
            
            elif self.block_type == "logo_cloud":
                logos = []
                for line in self.logocloud_items.get("1.0", "end-1c").strip().split("\n"):
                    if "|" in line:
                        parts = line.split("|", 1)
                        logos.append({"name": parts[0].strip(), "url": parts[1].strip()})
                self.result = LogoCloudBlock({
                    "title": self.logocloud_title.get(),
                    "logos": logos,
                    "columns": int(self.logocloud_cols.get()),
                    "grayscale": self.logocloud_gray.get(),
                    "logo_height": 50
                })
            
            elif self.block_type == "number_highlight":
                self.result = NumberHighlightBlock({
                    "number": self.numhl_number.get(),
                    "suffix": self.numhl_suffix.get(),
                    "prefix": self.numhl_prefix.get(),
                    "label": self.numhl_label.get(),
                    "style": self.numhl_style.get(),
                    "color": KRYSTO_PRIMARY
                })
            
            elif self.block_type == "divider_icon":
                self.result = DividerIconBlock({
                    "icon": self.divicon_icon.get(),
                    "line_style": self.divicon_style.get(),
                    "color": "#e0e0e0",
                    "icon_color": KRYSTO_PRIMARY,
                    "icon_size": 24
                })
            
            elif self.block_type == "qr_code":
                self.result = QRCodeBlock({
                    "url": self.qr_url.get(),
                    "size": int(self.qr_size.get() or 150),
                    "label": self.qr_label.get(),
                    "style": self.qr_style.get()
                })
            
            elif self.block_type == "faq":
                items = []
                for line in self.faq_items.get("1.0", "end-1c").strip().split("\n"):
                    if "Q:" in line and "| R:" in line:
                        parts = line.split("| R:")
                        q = parts[0].replace("Q:", "").strip()
                        a = parts[1].strip() if len(parts) > 1 else ""
                        items.append({"question": q, "answer": a})
                self.result = FaqBlock({
                    "title": self.faq_title.get(),
                    "items": items,
                    "style": self.faq_style.get()
                })
            
            elif self.block_type == "comparison":
                feat1 = [f.strip() for f in self.comp_feat1.get("1.0", "end-1c").strip().split("\n") if f.strip()]
                feat2 = [f.strip() for f in self.comp_feat2.get("1.0", "end-1c").strip().split("\n") if f.strip()]
                self.result = ComparisonBlock({
                    "title": self.comp_title.get(),
                    "option_1": {"name": self.comp_name1.get(), "features": feat1, "price": self.comp_price1.get(), "highlight": False},
                    "option_2": {"name": self.comp_name2.get(), "features": feat2, "price": self.comp_price2.get(), "highlight": self.comp_hl2.get()},
                    "style": "cards"
                })
            
            elif self.block_type == "coupon":
                self.result = CouponBlock({
                    "title": self.coupon_entries['coupon_title'].get(),
                    "value": self.coupon_entries['coupon_value'].get(),
                    "description": self.coupon_entries['coupon_desc'].get(),
                    "code": self.coupon_entries['coupon_code'].get(),
                    "expiry": self.coupon_entries['coupon_expiry'].get(),
                    "style": self.coupon_style.get()
                })
            
            elif self.block_type == "steps":
                steps = []
                for line in self.steps_items.get("1.0", "end-1c").strip().split("\n"):
                    if "|" in line:
                        parts = line.split("|", 1)
                        steps.append({"title": parts[0].strip(), "description": parts[1].strip()})
                self.result = StepsBlock({
                    "title": self.steps_title.get(),
                    "steps": steps,
                    "style": self.steps_style.get()
                })
            
            elif self.block_type == "highlight_box":
                self.result = HighlightBoxBlock({
                    "title": self.hlbox_title.get(),
                    "text": self.hlbox_text.get("1.0", "end-1c"),
                    "style": self.hlbox_style.get(),
                    "icon": self.hlbox_icon.get()
                })
            
            if self.on_save and self.result: self.on_save(self.result)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))


# ============================================================================
# FRAMES UI - CLIENTS
# ============================================================================
class ClientsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._create_ui()
        self._load_clients()
    
    def _create_ui(self):
        header = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="👥 Clients", font=("Helvetica", 20, "bold")).pack(side="left", padx=20, pady=15)
        ctk.CTkButton(header, text="➕ Nouveau", fg_color=KRYSTO_PRIMARY,
                      command=self._add).pack(side="right", padx=20, pady=10)
        
        # Filtres
        filter_frame = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(filter_frame, text="Filtrer:").pack(side="left", padx=15, pady=10)
        self.filter_type = ctk.CTkSegmentedButton(filter_frame, values=["Tous", "Pro", "Particulier", "Prospect", "Avec dette"],
                                                   command=self._filter_changed)
        self.filter_type.pack(side="left", padx=10, pady=10)
        self.filter_type.set("Tous")
        
        self.count_label = ctk.CTkLabel(filter_frame, text="0 client(s)", text_color=KRYSTO_SECONDARY)
        self.count_label.pack(side="right", padx=15)
        
        # Liste
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=KRYSTO_DARK)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _filter_changed(self, val):
        self._load_clients()
    
    def _load_clients(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        
        f = self.filter_type.get()
        if f == "Tous": clients = get_all_clients()
        elif f == "Pro": clients = get_all_clients(client_type="professionnel")
        elif f == "Particulier": clients = get_all_clients(client_type="particulier")
        elif f == "Prospect": clients = get_all_prospects()
        else: clients = get_all_clients(with_debt=True)
        
        self.count_label.configure(text=f"{len(clients)} client(s)")
        
        for c in clients:
            self._create_client_row(c)
    
    def _create_client_row(self, client):
        bloque = client['bloque'] if 'bloque' in client.keys() else 0
        bg_color = "#3a1a1a" if bloque else "#2a2a2a"
        
        frame = ctk.CTkFrame(self.list_frame, fg_color=bg_color)
        frame.pack(fill="x", pady=3, padx=5)
        
        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
        
        row1 = ctk.CTkFrame(info, fg_color="transparent")
        row1.pack(fill="x")
        
        name = client['name'] if 'name' in client.keys() else "Sans nom"
        ctk.CTkLabel(row1, text=name, font=("Helvetica", 13, "bold")).pack(side="left")
        
        # Badge bloqué
        if bloque:
            ctk.CTkLabel(row1, text="🚫 BLOQUÉ", text_color="#dc3545", 
                         font=("Helvetica", 10, "bold")).pack(side="left", padx=10)
        
        ctype = client['client_type'] if 'client_type' in client.keys() else 'particulier'
        badge_color = KRYSTO_PRIMARY if ctype == 'professionnel' else KRYSTO_SECONDARY
        ctk.CTkLabel(row1, text="PRO" if ctype == 'professionnel' else "PART",
                     text_color=badge_color, font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        
        # Afficher RIDET pour les pros
        if ctype == 'professionnel':
            ridet = client['ridet'] if 'ridet' in client.keys() and client['ridet'] else None
            if ridet:
                ctk.CTkLabel(row1, text=f"RIDET: {ridet}", text_color="#888", 
                             font=("Helvetica", 10)).pack(side="left", padx=5)
        
        newsletter = client['newsletter'] if 'newsletter' in client.keys() else 1
        if newsletter: ctk.CTkLabel(row1, text="📧", font=("Helvetica", 12)).pack(side="left")
        
        # Badge prospect
        is_prospect = bool(client['is_prospect']) if 'is_prospect' in client.keys() else False
        if is_prospect:
            ctk.CTkLabel(row1, text="🎯 PROSPECT", text_color="#f39c12", 
                         font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        
        # Afficher dettes pour les pros
        if ctype == 'professionnel':
            m1 = client['dette_m1'] if 'dette_m1' in client.keys() else 0
            m2 = client['dette_m2'] if 'dette_m2' in client.keys() else 0
            m3 = client['dette_m3'] if 'dette_m3' in client.keys() else 0
            m3p = client['dette_m3plus'] if 'dette_m3plus' in client.keys() else 0
            total = (m1 or 0) + (m2 or 0) + (m3 or 0) + (m3p or 0)
            if total > 0:
                # Calculer les jours restants pour chaque niveau
                date_m1 = client['date_dette_m1'] if 'date_dette_m1' in client.keys() else None
                date_m2 = client['date_dette_m2'] if 'date_dette_m2' in client.keys() else None
                date_m3 = client['date_dette_m3'] if 'date_dette_m3' in client.keys() else None
                
                def get_days_text(date_str, amount):
                    if not date_str or not amount:
                        return ""
                    try:
                        dt = datetime.fromisoformat(date_str)
                        days = (datetime.now() - dt).days
                        remaining = 30 - days
                        if remaining > 0:
                            return f"({remaining}j)"
                        else:
                            return "(⚠️)"
                    except:
                        return ""
                
                m1_days = get_days_text(date_m1, m1)
                m2_days = get_days_text(date_m2, m2)
                m3_days = get_days_text(date_m3, m3)
                
                dette_text = f"💰 M1:{format_price(m1 or 0)}{m1_days} M2:{format_price(m2 or 0)}{m2_days} M3:{format_price(m3 or 0)}{m3_days} M3+:{format_price(m3p or 0)}"
                ctk.CTkLabel(row1, text=dette_text, text_color="#ff6b6b", font=("Helvetica", 10)).pack(side="left", padx=15)
        
        email = client['email'] if 'email' in client.keys() else ''
        phone = client['phone'] if 'phone' in client.keys() else ''
        ctk.CTkLabel(info, text=f"📧 {email or '-'} | 📞 {phone or '-'}", text_color="#888",
                     font=("Helvetica", 11)).pack(anchor="w")
        
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(side="right", padx=10)
        ctk.CTkButton(btns, text="✏️", width=35, fg_color=KRYSTO_PRIMARY,
                      command=lambda: self._edit(client)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                      command=lambda: self._delete(client)).pack(side="left", padx=2)
    
    def _add(self):
        ClientDialog(self, on_save=self._load_clients)
    
    def _edit(self, client):
        ClientDialog(self, client=client, on_save=self._load_clients)
    
    def _delete(self, client):
        name = client['name'] if 'name' in client.keys() else "ce client"
        if messagebox.askyesno("Confirmation", f"Supprimer '{name}' ?"):
            delete_client(client['id'])
            self._load_clients()


class ClientDialog(ctk.CTkToplevel):
    def __init__(self, parent, client=None, on_save=None):
        super().__init__(parent)
        self.client = client
        self.on_save = on_save
        self.title("Client" if not client else "Modifier client")
        self.geometry("500x800")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text="👤 Informations", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Nom
        ctk.CTkLabel(main, text="Nom / Raison sociale *").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(main, height=38)
        self.name_entry.pack(fill="x", pady=(0, 10))
        
        # Email
        ctk.CTkLabel(main, text="Email").pack(anchor="w")
        self.email_entry = ctk.CTkEntry(main, height=35)
        self.email_entry.pack(fill="x", pady=(0, 10))
        
        # Téléphone
        ctk.CTkLabel(main, text="Téléphone").pack(anchor="w")
        self.phone_entry = ctk.CTkEntry(main, height=35)
        self.phone_entry.pack(fill="x", pady=(0, 10))
        
        # Adresse
        ctk.CTkLabel(main, text="Adresse").pack(anchor="w")
        self.address_entry = ctk.CTkEntry(main, height=35)
        self.address_entry.pack(fill="x", pady=(0, 10))
        
        # Type
        row_type = ctk.CTkFrame(main, fg_color="transparent")
        row_type.pack(fill="x", pady=10)
        ctk.CTkLabel(row_type, text="Type:").pack(side="left")
        self.type_var = ctk.StringVar(value="particulier")
        ctk.CTkRadioButton(row_type, text="Particulier", variable=self.type_var, value="particulier",
                           command=self._type_changed).pack(side="left", padx=10)
        ctk.CTkRadioButton(row_type, text="Professionnel", variable=self.type_var, value="professionnel",
                           command=self._type_changed).pack(side="left", padx=10)
        
        # Newsletter
        self.newsletter_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(main, text="Inscrit à la newsletter", variable=self.newsletter_var).pack(anchor="w", pady=5)
        
        # Prospect / Client
        status_frame = ctk.CTkFrame(main, fg_color="transparent")
        status_frame.pack(fill="x", pady=5)
        self.prospect_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(status_frame, text="🎯 Prospect", variable=self.prospect_var, 
                        fg_color="#f39c12", hover_color="#e67e22",
                        command=self._prospect_changed).pack(side="left")
        self.prospect_label = ctk.CTkLabel(status_frame, text="(sera ajouté au groupe Prospects)", 
                                           text_color="#888", font=("Helvetica", 9))
        self.prospect_label.pack(side="left", padx=10)
        self.prospect_label.pack_forget()  # Masqué par défaut
        
        # Section Code Parrainage (lecture seule, visible si client existant)
        self.parrainage_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        self.parrainage_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(self.parrainage_frame, text="🎁 Code Parrainage", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        code_row = ctk.CTkFrame(self.parrainage_frame, fg_color="transparent")
        code_row.pack(fill="x", padx=10, pady=(0, 10))
        
        self.parrainage_label = ctk.CTkLabel(code_row, text="PARRAIN-XXXX", font=("Courier", 14, "bold"), 
                                              text_color=KRYSTO_SECONDARY)
        self.parrainage_label.pack(side="left")
        
        ctk.CTkLabel(code_row, text="(code unique pour ce client)", text_color="#888", 
                     font=("Helvetica", 9)).pack(side="left", padx=10)
        
        # Masquer si nouveau client
        if not self.client:
            self.parrainage_frame.pack_forget()
        
        # Section infos Pro NC
        self.pro_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        self.pro_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(self.pro_frame, text="🏢 Infos Entreprise (NC)", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=10)
        
        pro_grid = ctk.CTkFrame(self.pro_frame, fg_color="transparent")
        pro_grid.pack(fill="x", padx=10, pady=(0, 10))
        
        # RIDET
        row_ridet = ctk.CTkFrame(pro_grid, fg_color="transparent")
        row_ridet.pack(fill="x", pady=3)
        ctk.CTkLabel(row_ridet, text="N° RIDET:", width=120).pack(side="left")
        self.ridet_entry = ctk.CTkEntry(row_ridet, placeholder_text="Ex: 123456.001")
        self.ridet_entry.pack(side="left", fill="x", expand=True)
        
        # Forme juridique
        row_forme = ctk.CTkFrame(pro_grid, fg_color="transparent")
        row_forme.pack(fill="x", pady=3)
        ctk.CTkLabel(row_forme, text="Forme juridique:", width=120).pack(side="left")
        self.forme_combo = ctk.CTkComboBox(row_forme, values=["", "EI", "EURL", "SARL", "SAS", "SASU", "SA", "SNC", "Association", "Autre"],
                                            width=150)
        self.forme_combo.pack(side="left")
        self.forme_combo.set("")
        
        # Nom gérant
        row_gerant = ctk.CTkFrame(pro_grid, fg_color="transparent")
        row_gerant.pack(fill="x", pady=3)
        ctk.CTkLabel(row_gerant, text="Nom du gérant:", width=120).pack(side="left")
        self.gerant_entry = ctk.CTkEntry(row_gerant)
        self.gerant_entry.pack(side="left", fill="x", expand=True)
        
        # Section blocage (Pro uniquement)
        self.block_frame = ctk.CTkFrame(main, fg_color="#4a1a1a")
        self.block_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(self.block_frame, text="🚫 Blocage Client", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=10)
        
        block_row = ctk.CTkFrame(self.block_frame, fg_color="transparent")
        block_row.pack(fill="x", padx=10, pady=(0, 5))
        
        self.bloque_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(block_row, text="Client bloqué (plus de ventes)", variable=self.bloque_var,
                        fg_color="#dc3545", hover_color="#c82333").pack(side="left")
        
        ctk.CTkLabel(self.block_frame, text="Motif du blocage:").pack(anchor="w", padx=10)
        self.motif_entry = ctk.CTkEntry(self.block_frame, placeholder_text="Ex: Impayés > 90 jours")
        self.motif_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # Section dettes (Pro uniquement)
        self.debt_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        self.debt_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(self.debt_frame, text="💰 Suivi Impayés", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=10)
        
        debt_grid = ctk.CTkFrame(self.debt_frame, fg_color="transparent")
        debt_grid.pack(fill="x", padx=10, pady=(0, 10))
        
        self.debt_entries = {}
        self.debt_date_labels = {}
        for i, (key, label, date_key) in enumerate([
            ("dette_m1", "M1 (30j)", "date_dette_m1"), 
            ("dette_m2", "M2 (60j)", "date_dette_m2"), 
            ("dette_m3", "M3 (90j)", "date_dette_m3"), 
            ("dette_m3plus", "M3+ (>90j)", None)
        ]):
            col = ctk.CTkFrame(debt_grid, fg_color="transparent")
            col.pack(side="left", expand=True, padx=5)
            ctk.CTkLabel(col, text=label, font=("Helvetica", 10)).pack()
            entry = ctk.CTkEntry(col, width=80, placeholder_text="0")
            entry.pack()
            self.debt_entries[key] = entry
            # Label pour la date
            date_label = ctk.CTkLabel(col, text="", text_color="#888", font=("Helvetica", 8))
            date_label.pack()
            if date_key:
                self.debt_date_labels[date_key] = date_label
        
        ctk.CTkLabel(self.debt_frame, text="💡 Les dettes passent M1→M2→M3→M3+ après 30 jours automatiquement",
                     text_color="#888", font=("Helvetica", 9)).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Notes
        ctk.CTkLabel(main, text="Notes").pack(anchor="w", pady=(10, 0))
        self.notes_entry = ctk.CTkTextbox(main, height=60)
        self.notes_entry.pack(fill="x", pady=5)
        
        # Charger données
        if self.client:
            self._load_data()
        
        self._type_changed()
        
        # Boutons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="💾 Sauvegarder", fg_color=KRYSTO_PRIMARY, command=self._save).pack(side="left", expand=True, padx=5)
    
    def _load_data(self):
        c = self.client
        self.name_entry.insert(0, c['name'] if 'name' in c.keys() else '')
        self.email_entry.insert(0, c['email'] if 'email' in c.keys() and c['email'] else '')
        self.phone_entry.insert(0, c['phone'] if 'phone' in c.keys() and c['phone'] else '')
        self.address_entry.insert(0, c['address'] if 'address' in c.keys() and c['address'] else '')
        self.type_var.set(c['client_type'] if 'client_type' in c.keys() else 'particulier')
        self.newsletter_var.set(bool(c['newsletter']) if 'newsletter' in c.keys() else True)
        self.notes_entry.insert("1.0", c['notes'] if 'notes' in c.keys() and c['notes'] else '')
        
        # Prospect
        is_prospect = bool(c['is_prospect']) if 'is_prospect' in c.keys() else False
        self.prospect_var.set(is_prospect)
        self._prospect_changed()
        
        # Code parrainage
        code_parrainage = c['code_parrainage'] if 'code_parrainage' in c.keys() and c['code_parrainage'] else ''
        if code_parrainage:
            self.parrainage_label.configure(text=f"PARRAIN-{code_parrainage}")
            self.parrainage_frame.pack(fill="x", pady=10)
        else:
            self.parrainage_frame.pack_forget()
        
        # Champs NC
        self.ridet_entry.insert(0, c['ridet'] if 'ridet' in c.keys() and c['ridet'] else '')
        self.forme_combo.set(c['forme_juridique'] if 'forme_juridique' in c.keys() and c['forme_juridique'] else '')
        self.gerant_entry.insert(0, c['nom_gerant'] if 'nom_gerant' in c.keys() and c['nom_gerant'] else '')
        
        # Blocage
        self.bloque_var.set(bool(c['bloque']) if 'bloque' in c.keys() else False)
        self.motif_entry.insert(0, c['motif_blocage'] if 'motif_blocage' in c.keys() and c['motif_blocage'] else '')
        
        for key in ['dette_m1', 'dette_m2', 'dette_m3', 'dette_m3plus']:
            val = c[key] if key in c.keys() and c[key] else 0
            self.debt_entries[key].insert(0, str(int(val)))
        
        # Afficher les dates des dettes
        for date_key in ['date_dette_m1', 'date_dette_m2', 'date_dette_m3']:
            if date_key in self.debt_date_labels:
                date_val = c[date_key] if date_key in c.keys() and c[date_key] else None
                if date_val:
                    try:
                        dt = datetime.fromisoformat(date_val)
                        days = (datetime.now() - dt).days
                        date_str = dt.strftime("%d/%m/%Y")
                        self.debt_date_labels[date_key].configure(text=f"📅 {date_str} ({days}j)")
                    except:
                        self.debt_date_labels[date_key].configure(text="")
                else:
                    self.debt_date_labels[date_key].configure(text="")
    
    def _type_changed(self):
        if self.type_var.get() == "professionnel":
            self.pro_frame.pack(fill="x", pady=10)
            self.block_frame.pack(fill="x", pady=10)
            self.debt_frame.pack(fill="x", pady=10)
        else:
            self.pro_frame.pack_forget()
            self.block_frame.pack_forget()
            self.debt_frame.pack_forget()
    
    def _prospect_changed(self):
        """Appelé quand la case Prospect change."""
        if self.prospect_var.get():
            self.prospect_label.pack(side="left", padx=10)
        else:
            self.prospect_label.pack_forget()
    
    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Attention", "Le nom est obligatoire")
            return
        
        data = {
            'name': name, 'email': self.email_entry.get().strip(),
            'phone': self.phone_entry.get().strip(), 'address': self.address_entry.get().strip(),
            'client_type': self.type_var.get(), 'newsletter': self.newsletter_var.get(),
            'is_prospect': self.prospect_var.get(),
            'notes': self.notes_entry.get("1.0", "end-1c").strip(),
            'ridet': self.ridet_entry.get().strip() if self.type_var.get() == 'professionnel' else None,
            'forme_juridique': self.forme_combo.get() if self.type_var.get() == 'professionnel' else None,
            'nom_gerant': self.gerant_entry.get().strip() if self.type_var.get() == 'professionnel' else None,
            'bloque': self.bloque_var.get() if self.type_var.get() == 'professionnel' else False,
            'motif_blocage': self.motif_entry.get().strip() if self.bloque_var.get() else None,
            'date_blocage': datetime.now().isoformat() if self.bloque_var.get() else None,
            'dette_m1': float(self.debt_entries['dette_m1'].get() or 0),
            'dette_m2': float(self.debt_entries['dette_m2'].get() or 0),
            'dette_m3': float(self.debt_entries['dette_m3'].get() or 0),
            'dette_m3plus': float(self.debt_entries['dette_m3plus'].get() or 0),
        }
        
        client_id = save_client(data, self.client['id'] if self.client else None)
        
        # Gérer l'ajout/retrait du groupe Prospects
        manage_prospect_group(client_id, data['is_prospect'])
        
        if self.on_save: self.on_save()
        self.destroy()


# ============================================================================
# FRAMES UI - PRODUITS
# ============================================================================
class ProductsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._create_ui()
        self._load_products()
    
    def _create_ui(self):
        header = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="📦 Produits", font=("Helvetica", 20, "bold")).pack(side="left", padx=20, pady=15)
        ctk.CTkButton(header, text="➕ Nouveau", fg_color=KRYSTO_PRIMARY,
                      command=self._add).pack(side="right", padx=20, pady=10)
        
        self.count_label = ctk.CTkLabel(header, text="0 produit(s)", text_color=KRYSTO_SECONDARY)
        self.count_label.pack(side="right", padx=15)
        
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=KRYSTO_DARK)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _load_products(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        products = get_all_products()
        self.count_label.configure(text=f"{len(products)} produit(s)")
        
        for p in products:
            frame = ctk.CTkFrame(self.list_frame, fg_color="#2a2a2a")
            frame.pack(fill="x", pady=3, padx=5)
            
            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
            
            row1 = ctk.CTkFrame(info, fg_color="transparent")
            row1.pack(fill="x")
            
            name = p['name'] if 'name' in p.keys() else "Sans nom"
            ctk.CTkLabel(row1, text=name, font=("Helvetica", 13, "bold")).pack(side="left")
            
            # Indicateur photos
            image_url = p['image_url'] if 'image_url' in p.keys() and p['image_url'] else None
            image_url_2 = p['image_url_2'] if 'image_url_2' in p.keys() and p['image_url_2'] else None
            image_url_3 = p['image_url_3'] if 'image_url_3' in p.keys() and p['image_url_3'] else None
            nb_photos = sum(1 for img in [image_url, image_url_2, image_url_3] if img)
            if nb_photos > 0:
                ctk.CTkLabel(row1, text=f"🖼️ {nb_photos}", text_color=KRYSTO_SECONDARY,
                             font=("Helvetica", 10)).pack(side="left", padx=8)
            
            category = p['category'] if 'category' in p.keys() and p['category'] else ""
            if category:
                ctk.CTkLabel(row1, text=category, text_color="#888", 
                             font=("Helvetica", 10)).pack(side="left", padx=5)
            
            # Prix Particulier et Pro - accès sécurisé pour sqlite3.Row
            prix_part = (p['prix_particulier'] if 'prix_particulier' in p.keys() and p['prix_particulier'] else None) or (p['price'] if 'price' in p.keys() else 0) or 0
            prix_pro = (p['prix_pro'] if 'prix_pro' in p.keys() and p['prix_pro'] else None) or (p['price'] if 'price' in p.keys() else 0) or 0
            stock = p['stock'] if 'stock' in p.keys() else 0
            
            price_info = ctk.CTkFrame(info, fg_color="transparent")
            price_info.pack(anchor="w")
            
            ctk.CTkLabel(price_info, text=f"👤 Part: {format_price(prix_part)}", 
                         text_color="#17a2b8", font=("Helvetica", 10)).pack(side="left")
            ctk.CTkLabel(price_info, text=f"🏢 Pro: {format_price(prix_pro)}", 
                         text_color="#28a745", font=("Helvetica", 10)).pack(side="left", padx=10)
            ctk.CTkLabel(price_info, text=f"📦 Stock: {stock or 0}",
                         text_color="#888", font=("Helvetica", 10)).pack(side="left", padx=10)
            
            btns = ctk.CTkFrame(frame, fg_color="transparent")
            btns.pack(side="right", padx=10)
            ctk.CTkButton(btns, text="✏️", width=35, fg_color=KRYSTO_PRIMARY,
                          command=lambda prod=p: self._edit(prod)).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                          command=lambda prod=p: self._delete(prod)).pack(side="left", padx=2)
    
    def _add(self):
        ProductDialog(self, on_save=self._load_products)
    
    def _edit(self, product):
        ProductDialog(self, product=product, on_save=self._load_products)
    
    def _delete(self, product):
        name = product['name'] if 'name' in product.keys() else "ce produit"
        if messagebox.askyesno("Confirmation", f"Supprimer '{name}' ?"):
            delete_product(product['id'])
            self._load_products()


class ProductDialog(ctk.CTkToplevel):
    def __init__(self, parent, product=None, on_save=None):
        super().__init__(parent)
        self.product = product
        self.on_save = on_save
        self.title("Produit" if not product else "Modifier produit")
        self.geometry("550x750")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text="📦 Produit", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
        
        ctk.CTkLabel(main, text="Nom *").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(main, height=38)
        self.name_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main, text="Description").pack(anchor="w")
        self.desc_entry = ctk.CTkTextbox(main, height=60)
        self.desc_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main, text="Catégorie").pack(anchor="w")
        self.cat_entry = ctk.CTkEntry(main, height=35)
        self.cat_entry.pack(fill="x", pady=(0, 10))
        
        # Section prix avec deux tarifs
        prix_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK, corner_radius=10)
        prix_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(prix_frame, text="💰 Tarification", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=15, pady=10)
        
        prix_row = ctk.CTkFrame(prix_frame, fg_color="transparent")
        prix_row.pack(fill="x", padx=15, pady=(0, 10))
        
        col1 = ctk.CTkFrame(prix_row, fg_color="transparent")
        col1.pack(side="left", expand=True)
        ctk.CTkLabel(col1, text="Prix Particulier (XPF)", text_color="#17a2b8").pack(anchor="w")
        self.prix_particulier_entry = ctk.CTkEntry(col1, width=130, placeholder_text="0")
        self.prix_particulier_entry.pack(anchor="w")
        
        col2 = ctk.CTkFrame(prix_row, fg_color="transparent")
        col2.pack(side="left", expand=True)
        ctk.CTkLabel(col2, text="Prix Pro (XPF)", text_color="#28a745").pack(anchor="w")
        self.prix_pro_entry = ctk.CTkEntry(col2, width=130, placeholder_text="0")
        self.prix_pro_entry.pack(anchor="w")
        
        ctk.CTkLabel(prix_frame, text="💡 Le prix s'applique automatiquement selon le type de client", 
                     text_color="#888", font=("Helvetica", 9)).pack(anchor="w", padx=15, pady=(0, 10))
        
        # Coût et Stock
        row2 = ctk.CTkFrame(main, fg_color="transparent")
        row2.pack(fill="x", pady=10)
        
        col_cost = ctk.CTkFrame(row2, fg_color="transparent")
        col_cost.pack(side="left", expand=True)
        ctk.CTkLabel(col_cost, text="Coût d'achat (XPF)").pack(anchor="w")
        self.cost_entry = ctk.CTkEntry(col_cost, width=120)
        self.cost_entry.pack(anchor="w")
        
        col_stock = ctk.CTkFrame(row2, fg_color="transparent")
        col_stock.pack(side="left", expand=True)
        ctk.CTkLabel(col_stock, text="Stock").pack(anchor="w")
        self.stock_entry = ctk.CTkEntry(col_stock, width=80)
        self.stock_entry.pack(anchor="w")
        
        # Section images
        img_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        img_frame.pack(fill="x", pady=15)
        
        ctk.CTkLabel(img_frame, text="🖼️ Photos du produit", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=10)
        
        ctk.CTkLabel(img_frame, text="Image principale (URL):").pack(anchor="w", padx=10)
        self.image_url_entry = ctk.CTkEntry(img_frame, placeholder_text="https://...")
        self.image_url_entry.pack(fill="x", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(img_frame, text="Image 2 (URL):").pack(anchor="w", padx=10)
        self.image_url_2_entry = ctk.CTkEntry(img_frame, placeholder_text="https://...")
        self.image_url_2_entry.pack(fill="x", padx=10, pady=(0, 8))
        
        ctk.CTkLabel(img_frame, text="Image 3 (URL):").pack(anchor="w", padx=10)
        self.image_url_3_entry = ctk.CTkEntry(img_frame, placeholder_text="https://...")
        self.image_url_3_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        self.active_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(main, text="Produit actif", variable=self.active_var).pack(anchor="w", pady=10)
        
        if self.product:
            p = self.product
            self.name_entry.insert(0, p['name'] if 'name' in p.keys() else '')
            self.desc_entry.insert("1.0", p['description'] if 'description' in p.keys() and p['description'] else '')
            self.cat_entry.insert(0, p['category'] if 'category' in p.keys() and p['category'] else '')
            
            # Prix - utiliser les nouveaux champs ou fallback sur price
            prix_part = (p['prix_particulier'] if 'prix_particulier' in p.keys() and p['prix_particulier'] else None) or (p['price'] if 'price' in p.keys() else 0) or 0
            prix_pro = (p['prix_pro'] if 'prix_pro' in p.keys() and p['prix_pro'] else None) or (p['price'] if 'price' in p.keys() else 0) or 0
            self.prix_particulier_entry.insert(0, str(int(prix_part)))
            self.prix_pro_entry.insert(0, str(int(prix_pro)))
            
            self.cost_entry.insert(0, str(p['cost'] if 'cost' in p.keys() else 0))
            self.stock_entry.insert(0, str(p['stock'] if 'stock' in p.keys() else 0))
            self.image_url_entry.insert(0, p['image_url'] if 'image_url' in p.keys() and p['image_url'] else '')
            self.image_url_2_entry.insert(0, p['image_url_2'] if 'image_url_2' in p.keys() and p['image_url_2'] else '')
            self.image_url_3_entry.insert(0, p['image_url_3'] if 'image_url_3' in p.keys() and p['image_url_3'] else '')
            self.active_var.set(bool(p['active']) if 'active' in p.keys() else True)
        
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="💾 OK", fg_color=KRYSTO_PRIMARY, command=self._save).pack(side="left", expand=True, padx=5)
    
    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Attention", "Le nom est obligatoire")
            return
        
        prix_particulier = float(self.prix_particulier_entry.get() or 0)
        prix_pro = float(self.prix_pro_entry.get() or 0)
        
        data = {
            'name': name, 
            'description': self.desc_entry.get("1.0", "end-1c").strip(),
            'category': self.cat_entry.get().strip(),
            'price': prix_particulier,  # Garder compatibilité avec l'ancien champ
            'prix_particulier': prix_particulier,
            'prix_pro': prix_pro,
            'cost': float(self.cost_entry.get() or 0),
            'stock': int(self.stock_entry.get() or 0), 
            'active': self.active_var.get(),
            'image_url': self.image_url_entry.get().strip() or None,
            'image_url_2': self.image_url_2_entry.get().strip() or None,
            'image_url_3': self.image_url_3_entry.get().strip() or None,
        }
        save_product(data, self.product['id'] if self.product else None)
        if self.on_save: self.on_save()
        self.destroy()


# ============================================================================
# FRAMES UI - DÉPÔTS-VENTES
# ============================================================================
class DepotsFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._create_ui()
        self._load_depots()
    
    def _create_ui(self):
        header = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="🏪 Dépôts-Ventes", font=("Helvetica", 20, "bold")).pack(side="left", padx=20, pady=15)
        ctk.CTkButton(header, text="➕ Nouveau dépôt", fg_color=KRYSTO_PRIMARY,
                      command=self._add_depot).pack(side="right", padx=20, pady=10)
        
        self.count_label = ctk.CTkLabel(header, text="0 dépôt(s)", text_color=KRYSTO_SECONDARY)
        self.count_label.pack(side="right", padx=15)
        
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=KRYSTO_DARK)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _load_depots(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        depots = get_all_depots()
        self.count_label.configure(text=f"{len(depots)} dépôt(s)")
        
        for d in depots:
            self._create_depot_card(d)
    
    def _create_depot_card(self, depot):
        card = ctk.CTkFrame(self.list_frame, fg_color="#2a2a2a")
        card.pack(fill="x", pady=5, padx=5)
        
        # Header du dépôt
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=10)
        
        # Nom du client (lié)
        client_name = depot['client_name'] if 'client_name' in depot.keys() else "Client inconnu"
        ctk.CTkLabel(header, text=f"🏪 {client_name}", font=("Helvetica", 14, "bold")).pack(side="left")
        
        # RIDET
        ridet = depot['client_ridet'] if 'client_ridet' in depot.keys() and depot['client_ridet'] else None
        if ridet:
            ctk.CTkLabel(header, text=f"RIDET: {ridet}", text_color="#888",
                         font=("Helvetica", 10)).pack(side="left", padx=10)
        
        commission = depot['commission_percent'] if 'commission_percent' in depot.keys() else 0
        ctk.CTkLabel(header, text=f"Commission: {commission}%", text_color=KRYSTO_SECONDARY,
                     font=("Helvetica", 11)).pack(side="left", padx=10)
        
        # Stats
        stats = get_depot_stats(depot['id'])
        in_stock = stats.get('in_stock') or 0
        sold = stats.get('total_sold') or 0
        
        ctk.CTkLabel(header, text=f"📦 En stock: {int(in_stock)} | ✅ Vendus: {int(sold)}",
                     text_color="#888", font=("Helvetica", 11)).pack(side="left", padx=15)
        
        # Boutons
        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.pack(side="right")
        
        ctk.CTkButton(btns, text="📋 Détails", width=80, fg_color=KRYSTO_PRIMARY,
                      command=lambda: self._view_depot(depot)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="✏️", width=35, fg_color="gray",
                      command=lambda: self._edit_depot(depot)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                      command=lambda: self._delete_depot(depot)).pack(side="left", padx=2)
        
        # Ligne 2: Contact + boutons email
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=(0, 10))
        
        client_email = depot['client_email'] if 'client_email' in depot.keys() else ''
        client_phone = depot['client_phone'] if 'client_phone' in depot.keys() else ''
        ctk.CTkLabel(row2, text=f"📧 {client_email or '-'} | 📞 {client_phone or '-'}",
                     text_color="#666", font=("Helvetica", 10)).pack(side="left")
        
        # Boutons email
        email_btns = ctk.CTkFrame(row2, fg_color="transparent")
        email_btns.pack(side="right")
        
        ctk.CTkButton(email_btns, text="📧 Réappro?", width=90, height=28, fg_color=KRYSTO_SECONDARY, 
                      text_color=KRYSTO_DARK, command=lambda: self._send_restock_email(depot)).pack(side="left", padx=2)
        ctk.CTkButton(email_btns, text="🎉 Nouveautés", width=90, height=28, fg_color=KRYSTO_PRIMARY,
                      command=lambda: self._send_new_products_email(depot)).pack(side="left", padx=2)
    
    def _add_depot(self):
        DepotDialog(self, on_save=self._load_depots)
    
    def _edit_depot(self, depot):
        DepotDialog(self, depot=depot, on_save=self._load_depots)
    
    def _delete_depot(self, depot):
        name = depot['client_name'] if 'client_name' in depot.keys() else "ce dépôt"
        if messagebox.askyesno("Confirmation", f"Supprimer le dépôt '{name}' et tous ses produits ?"):
            delete_depot(depot['id'])
            self._load_depots()
    
    def _view_depot(self, depot):
        DepotDetailDialog(self, depot)
    
    def _send_restock_email(self, depot):
        """Envoie un email pour demander si besoin de réappro."""
        name = depot['client_name'] if 'client_name' in depot.keys() else "le dépôt"
        if messagebox.askyesno("Confirmation", f"Envoyer un email de réapprovisionnement à {name} ?"):
            success, msg = send_depot_email(depot['id'], "restock")
            if success:
                messagebox.showinfo("Succès", "Email envoyé!")
            else:
                messagebox.showerror("Erreur", msg)
    
    def _send_new_products_email(self, depot):
        """Ouvre un dialogue pour sélectionner les nouveaux produits à proposer."""
        NewProductsEmailDialog(self, depot)


class DepotDialog(ctk.CTkToplevel):
    def __init__(self, parent, depot=None, on_save=None):
        super().__init__(parent)
        self.depot = depot
        self.on_save = on_save
        self.title("Nouveau dépôt-vente" if not depot else "Modifier dépôt-vente")
        self.geometry("450x350")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text="🏪 Dépôt-Vente", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Sélection du client pro
        ctk.CTkLabel(main, text="Client professionnel *").pack(anchor="w")
        
        # Récupérer les clients pro
        if self.depot:
            # En édition, on peut garder le même client ou en choisir un autre
            pro_clients = get_pro_clients()
        else:
            # En création, on propose uniquement les clients sans dépôt
            pro_clients = get_clients_without_depot()
        
        self.client_map = {}
        client_names = []
        for c in pro_clients:
            name = c['name'] if 'name' in c.keys() else "Sans nom"
            self.client_map[name] = c['id']
            client_names.append(name)
        
        if not client_names and not self.depot:
            ctk.CTkLabel(main, text="⚠️ Aucun client pro disponible.\nCréez d'abord un client professionnel.", 
                         text_color="#ff6b6b").pack(pady=20)
            ctk.CTkButton(main, text="Fermer", fg_color="gray", command=self.destroy).pack()
            return
        
        self.client_combo = ctk.CTkComboBox(main, values=client_names, width=350, state="readonly")
        self.client_combo.pack(anchor="w", pady=(0, 15))
        
        # Si édition, présélectionner le client actuel
        if self.depot and 'client_name' in self.depot.keys():
            current_name = self.depot['client_name']
            if current_name in client_names:
                self.client_combo.set(current_name)
            elif client_names:
                self.client_combo.set(client_names[0])
        elif client_names:
            self.client_combo.set(client_names[0])
        
        # Commission
        ctk.CTkLabel(main, text="Commission (%)").pack(anchor="w", pady=(10, 0))
        self.commission_entry = ctk.CTkEntry(main, width=100, placeholder_text="0")
        self.commission_entry.pack(anchor="w", pady=(0, 10))
        
        # Notes
        ctk.CTkLabel(main, text="Notes spécifiques au dépôt").pack(anchor="w")
        self.notes_entry = ctk.CTkTextbox(main, height=60)
        self.notes_entry.pack(fill="x", pady=(0, 10))
        
        # Charger les données existantes
        if self.depot:
            commission = self.depot['commission_percent'] if 'commission_percent' in self.depot.keys() else 0
            self.commission_entry.insert(0, str(commission or 0))
            notes = self.depot['notes'] if 'notes' in self.depot.keys() and self.depot['notes'] else ''
            self.notes_entry.insert("1.0", notes)
        
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="💾 OK", fg_color=KRYSTO_PRIMARY, command=self._save).pack(side="left", expand=True, padx=5)
    
    def _save(self):
        if not hasattr(self, 'client_combo'):
            self.destroy()
            return
            
        client_name = self.client_combo.get()
        if not client_name or client_name not in self.client_map:
            messagebox.showwarning("Attention", "Sélectionnez un client")
            return
        
        data = {
            'client_id': self.client_map[client_name],
            'commission_percent': float(self.commission_entry.get() or 0),
            'notes': self.notes_entry.get("1.0", "end-1c").strip(),
            'active': 1
        }
        save_depot(data, self.depot['id'] if self.depot else None)
        if self.on_save: self.on_save()
        self.destroy()


class DepotDetailDialog(ctk.CTkToplevel):
    def __init__(self, parent, depot):
        super().__init__(parent)
        self.depot = depot
        self.parent_frame = parent
        client_name = depot['client_name'] if 'client_name' in depot.keys() else "Dépôt"
        self.title(f"Dépôt: {client_name}")
        self.geometry("750x600")
        self.transient(parent)
        self._create_ui()
        self._load_products()
    
    def _create_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Header
        header = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        header.pack(fill="x", pady=(0, 10))
        
        client_name = self.depot['client_name'] if 'client_name' in self.depot.keys() else "Dépôt"
        ctk.CTkLabel(header, text=f"🏪 {client_name}", font=("Helvetica", 16, "bold")).pack(side="left", padx=15, pady=10)
        
        # Boutons header
        btns = ctk.CTkFrame(header, fg_color="transparent")
        btns.pack(side="right", padx=10, pady=10)
        
        ctk.CTkButton(btns, text="💰 Récupérer fonds", fg_color="#28a745", width=140,
                      command=self._collect_funds).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="➕ Déposer produits", fg_color=KRYSTO_PRIMARY, width=140,
                      command=self._add_products).pack(side="left", padx=5)
        
        # Stats
        self.stats_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        self.stats_frame.pack(fill="x", pady=(0, 10))
        self._update_stats()
        
        # Liste produits
        self.products_frame = ctk.CTkScrollableFrame(main, fg_color="#1a1a1a")
        self.products_frame.pack(fill="both", expand=True)
    
    def _update_stats(self):
        """Met à jour les statistiques du dépôt."""
        for w in self.stats_frame.winfo_children():
            w.destroy()
        
        stats = get_depot_stats(self.depot['id'])
        
        sold = int(stats.get('total_sold') or 0)
        invoiced = int(stats.get('total_invoiced') or 0)
        to_collect = sold - invoiced
        
        for label, val, color in [("Déposés", stats.get('total_deposited') or 0, "#888"),
                                   ("En stock", stats.get('in_stock') or 0, KRYSTO_PRIMARY),
                                   ("Vendus", sold, KRYSTO_SECONDARY),
                                   ("Facturés", invoiced, "#28a745"),
                                   ("À récupérer", to_collect, "#ff6b6b" if to_collect > 0 else "#888")]:
            col = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            col.pack(side="left", expand=True, pady=10)
            ctk.CTkLabel(col, text=str(int(val)), font=("Helvetica", 18, "bold"), text_color=color).pack()
            ctk.CTkLabel(col, text=label, font=("Helvetica", 10), text_color="#888").pack()
    
    def _load_products(self):
        for w in self.products_frame.winfo_children(): w.destroy()
        
        products = get_depot_products(self.depot['id'])
        
        if not products:
            ctk.CTkLabel(self.products_frame, text="Aucun produit en dépôt", text_color="#666").pack(pady=30)
            return
        
        for dp in products:
            frame = ctk.CTkFrame(self.products_frame, fg_color="#2a2a2a")
            frame.pack(fill="x", pady=2, padx=5)
            
            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=15, pady=8)
            
            name = dp['product_name'] if 'product_name' in dp.keys() else "Produit"
            deposited = int(dp['quantity_deposited'] if 'quantity_deposited' in dp.keys() else 0)
            sold = int(dp['quantity_sold'] if 'quantity_sold' in dp.keys() else 0)
            returned = int(dp['quantity_returned'] if 'quantity_returned' in dp.keys() else 0)
            invoiced = int(dp['quantity_invoiced'] if 'quantity_invoiced' in dp.keys() else 0)
            in_stock = deposited - sold - returned
            to_collect = sold - invoiced
            
            ctk.CTkLabel(info, text=name, font=("Helvetica", 12, "bold")).pack(side="left")
            
            stats_text = f"📦 Stock: {in_stock} | ✅ Vendus: {sold}"
            if to_collect > 0:
                stats_text += f" | 💰 À facturer: {to_collect}"
            ctk.CTkLabel(info, text=stats_text, text_color="#888", font=("Helvetica", 10)).pack(side="left", padx=15)
            
            btns = ctk.CTkFrame(frame, fg_color="transparent")
            btns.pack(side="right", padx=10)
            
            ctk.CTkButton(btns, text="✅ Vente", width=70, height=28, fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK,
                          command=lambda p=dp: self._record_sale(p)).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="↩️ Retour", width=70, height=28, fg_color="gray",
                          command=lambda p=dp: self._record_return(p)).pack(side="left", padx=2)
    
    def _add_products(self):
        dialog = AddDepotProductDialog(self, self.depot['id'])
        self.wait_window(dialog)
        self._update_stats()
        self._load_products()
    
    def _record_sale(self, dp):
        qty = ctk.CTkInputDialog(text="Quantité vendue:", title="Enregistrer vente").get_input()
        if qty and qty.isdigit() and int(qty) > 0:
            product_id = dp['product_id'] if 'product_id' in dp.keys() else None
            if product_id:
                record_depot_sale(self.depot['id'], product_id, int(qty))
                self._update_stats()
                self._load_products()
    
    def _record_return(self, dp):
        qty = ctk.CTkInputDialog(text="Quantité retournée:", title="Enregistrer retour").get_input()
        if qty and qty.isdigit() and int(qty) > 0:
            product_id = dp['product_id'] if 'product_id' in dp.keys() else None
            if product_id:
                record_depot_return(self.depot['id'], product_id, int(qty))
                self._update_stats()
                self._load_products()
    
    def _collect_funds(self):
        """Récupère les fonds des ventes et crée une facture."""
        # Vérifier s'il y a des ventes à facturer
        products_to_invoice = get_depot_sales_to_invoice(self.depot['id'])
        
        if not products_to_invoice:
            messagebox.showinfo("Information", "Aucune vente à facturer pour ce dépôt.")
            return
        
        # Calculer le total estimé
        total_qty = 0
        total_amount = 0
        for p in products_to_invoice:
            qty = p['quantity_sold'] - (p.get('quantity_invoiced') or 0)
            price = p.get('price_depot') or p.get('prix_pro') or p.get('prix_particulier') or 0
            discount = p.get('discount_percent') or 0
            total_qty += qty
            total_amount += price * qty * (1 - discount / 100)
        
        # Calculer TGC
        tgc = total_amount * 0.11
        total_ttc = total_amount + tgc
        
        # Confirmation
        msg = f"""Créer une facture pour les ventes du dépôt ?

📦 Produits à facturer: {len(products_to_invoice)}
📊 Quantité totale: {int(total_qty)}
💰 Montant HT: {format_price(total_amount)}
📋 TGC (11%): {format_price(tgc)}
💵 TOTAL TTC: {format_price(total_ttc)}

Cette facture sera enregistrée dans le CA."""
        
        if not messagebox.askyesno("Récupérer fonds", msg):
            return
        
        # Créer la facture
        invoice_id, result = create_depot_invoice(self.depot['id'])
        
        if invoice_id is None:
            messagebox.showerror("Erreur", str(result))
            return
        
        # Récupérer le numéro de facture
        invoice, _ = get_invoice(invoice_id)
        invoice_number = invoice['number'] if invoice else f"#{invoice_id}"
        
        messagebox.showinfo("Facture créée", 
            f"""✅ Facture {invoice_number} créée !

💰 Total: {format_price(result['total'])}
📦 {result['nb_products']} produit(s) facturé(s)

La facture a été enregistrée dans le CA.""")
        
        # Rafraîchir l'affichage
        self._update_stats()
        self._load_products()


class AddDepotProductDialog(ctk.CTkToplevel):
    def __init__(self, parent, depot_id):
        super().__init__(parent)
        self.depot_id = depot_id
        self.depot = get_depot(depot_id)
        self.title("Déposer des produits")
        self.geometry("500x550")
        self.transient(parent)
        self.grab_set()
        self.items_to_deposit = []
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        client_name = self.depot['client_name'] if self.depot and 'client_name' in self.depot.keys() else "Client"
        ctk.CTkLabel(main, text=f"➕ Dépôt chez: {client_name}", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Ajouter un produit
        add_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        add_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(add_frame, text="Ajouter un produit", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=10)
        
        # Sélection produit
        row1 = ctk.CTkFrame(add_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="Produit:", width=80).pack(side="left")
        
        products = get_all_products()
        self.product_map = {p['name']: p for p in products}
        product_names = list(self.product_map.keys())
        
        self.product_combo = ctk.CTkComboBox(row1, values=product_names, width=280)
        self.product_combo.pack(side="left", padx=5)
        if product_names: self.product_combo.set(product_names[0])
        
        # Quantité et remise
        row2 = ctk.CTkFrame(add_frame, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(row2, text="Quantité:", width=80).pack(side="left")
        self.qty_entry = ctk.CTkEntry(row2, width=60)
        self.qty_entry.pack(side="left", padx=5)
        self.qty_entry.insert(0, "1")
        
        ctk.CTkLabel(row2, text="Remise %:", width=70).pack(side="left", padx=(15, 0))
        self.discount_entry = ctk.CTkEntry(row2, width=60)
        self.discount_entry.pack(side="left", padx=5)
        self.discount_entry.insert(0, "0")
        
        ctk.CTkButton(add_frame, text="➕ Ajouter à la liste", fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK,
                      command=self._add_item).pack(padx=10, pady=10)
        
        # Liste des produits à déposer
        ctk.CTkLabel(main, text="📋 Produits à déposer:", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(15, 5))
        
        self.items_frame = ctk.CTkScrollableFrame(main, height=180, fg_color="#1a1a1a")
        self.items_frame.pack(fill="x")
        
        self._refresh_items_list()
        
        # Boutons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="📄 Générer Bon PDF", fg_color=KRYSTO_PRIMARY, 
                      command=self._save_and_generate_pdf).pack(side="left", expand=True, padx=5)
    
    def _add_item(self):
        product_name = self.product_combo.get()
        if product_name not in self.product_map:
            messagebox.showwarning("Attention", "Sélectionnez un produit")
            return
        
        qty = int(self.qty_entry.get() or 0)
        if qty <= 0:
            messagebox.showwarning("Attention", "Quantité invalide")
            return
        
        discount = float(self.discount_entry.get() or 0)
        product = self.product_map[product_name]
        
        self.items_to_deposit.append({
            'product_id': product['id'],
            'product_name': product_name,
            'price': product['price'] if 'price' in product.keys() else 0,
            'quantity': qty,
            'discount': discount
        })
        
        self.qty_entry.delete(0, "end")
        self.qty_entry.insert(0, "1")
        self.discount_entry.delete(0, "end")
        self.discount_entry.insert(0, "0")
        
        self._refresh_items_list()
    
    def _refresh_items_list(self):
        for w in self.items_frame.winfo_children(): w.destroy()
        
        if not self.items_to_deposit:
            ctk.CTkLabel(self.items_frame, text="Aucun produit ajouté", text_color="#666").pack(pady=20)
            return
        
        for i, item in enumerate(self.items_to_deposit):
            row = ctk.CTkFrame(self.items_frame, fg_color="#2a2a2a")
            row.pack(fill="x", pady=2, padx=5)
            
            price_remise = item['price'] * (1 - item['discount']/100)
            info_text = f"{item['product_name']} x{item['quantity']} @ {format_price(price_remise)}"
            if item['discount'] > 0:
                info_text += f" (-{item['discount']}%)"
            
            ctk.CTkLabel(row, text=info_text, font=("Helvetica", 11)).pack(side="left", padx=10, pady=5)
            
            total = price_remise * item['quantity']
            ctk.CTkLabel(row, text=format_price(total), text_color=KRYSTO_SECONDARY,
                         font=("Helvetica", 11, "bold")).pack(side="right", padx=10)
            
            ctk.CTkButton(row, text="🗑️", width=30, height=25, fg_color="#dc3545",
                          command=lambda idx=i: self._remove_item(idx)).pack(side="right", padx=5)
    
    def _remove_item(self, idx):
        self.items_to_deposit.pop(idx)
        self._refresh_items_list()
    
    def _save_and_generate_pdf(self):
        if not self.items_to_deposit:
            messagebox.showwarning("Attention", "Ajoutez au moins un produit")
            return
        
        # Sauvegarder les dépôts
        for item in self.items_to_deposit:
            add_depot_product(self.depot_id, item['product_id'], item['quantity'], 
                              item['price'], item['discount'])
        
        # Générer le PDF
        pdf_path = generate_depot_receipt_pdf(self.depot, self.items_to_deposit)
        
        if pdf_path:
            messagebox.showinfo("Succès", f"Bon de dépôt généré:\n{pdf_path}")
            # Ouvrir le PDF
            import subprocess
            try:
                if os.name == 'nt': os.startfile(pdf_path)
                else: subprocess.run(['xdg-open', pdf_path], check=False)
            except: pass
        
        self.destroy()


def generate_depot_receipt_pdf(depot, items):
    """Génère un bon de dépôt-vente en PDF (double exemplaire)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        
        # Infos client
        client_name = depot['client_name'] if 'client_name' in depot.keys() else "Client"
        client_email = depot['client_email'] if 'client_email' in depot.keys() else ""
        client_phone = depot['client_phone'] if 'client_phone' in depot.keys() else ""
        client_address = depot['client_address'] if 'client_address' in depot.keys() else ""
        ridet = depot['client_ridet'] if 'client_ridet' in depot.keys() else ""
        forme_juridique = depot['client_forme'] if 'client_forme' in depot.keys() else ""
        
        commission = depot['commission_percent'] if 'commission_percent' in depot.keys() else 0
        
        # Numéro de bon
        bon_number = f"DEP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        date_str = datetime.now().strftime('%d/%m/%Y')
        
        # Créer le PDF
        filename = f"bon_depot_{bon_number}.pdf"
        filepath = os.path.join(os.path.expanduser("~"), filename)
        
        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4
        
        def draw_receipt(y_offset, exemplaire):
            """Dessine un exemplaire du bon."""
            y = height - 20*mm - y_offset
            
            # En-tête
            c.setFont("Helvetica-Bold", 16)
            c.drawString(20*mm, y, COMPANY_NAME)
            c.setFont("Helvetica", 9)
            c.drawString(20*mm, y - 5*mm, COMPANY_ADDRESS)
            c.drawString(20*mm, y - 9*mm, f"Email: {COMPANY_EMAIL}")
            
            # Titre
            c.setFont("Helvetica-Bold", 14)
            c.drawString(100*mm, y, "BON DE DÉPÔT-VENTE")
            c.setFont("Helvetica", 10)
            c.drawString(100*mm, y - 5*mm, f"N° {bon_number}")
            c.drawString(100*mm, y - 9*mm, f"Date: {date_str}")
            c.drawString(150*mm, y - 9*mm, f"({exemplaire})")
            
            # Ligne séparatrice
            y -= 15*mm
            c.setStrokeColor(colors.HexColor(KRYSTO_PRIMARY))
            c.setLineWidth(2)
            c.line(20*mm, y, width - 20*mm, y)
            
            # Infos dépositaire
            y -= 8*mm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(20*mm, y, "DÉPOSITAIRE:")
            c.setFont("Helvetica", 10)
            y -= 5*mm
            c.drawString(20*mm, y, client_name)
            if forme_juridique:
                c.drawString(100*mm, y, f"Forme: {forme_juridique}")
            y -= 4*mm
            if ridet:
                c.drawString(20*mm, y, f"RIDET: {ridet}")
            if client_address:
                y -= 4*mm
                c.drawString(20*mm, y, client_address)
            y -= 4*mm
            contact_info = []
            if client_phone: contact_info.append(f"Tél: {client_phone}")
            if client_email: contact_info.append(f"Email: {client_email}")
            c.drawString(20*mm, y, " | ".join(contact_info))
            
            # Tableau des produits
            y -= 10*mm
            c.setFont("Helvetica-Bold", 10)
            
            # En-tête tableau
            c.setFillColor(colors.HexColor(KRYSTO_PRIMARY))
            c.rect(20*mm, y - 5*mm, width - 40*mm, 6*mm, fill=True, stroke=False)
            c.setFillColor(colors.white)
            c.drawString(22*mm, y - 3.5*mm, "Produit")
            c.drawString(90*mm, y - 3.5*mm, "Qté")
            c.drawString(105*mm, y - 3.5*mm, "Prix unit.")
            c.drawString(130*mm, y - 3.5*mm, "Remise")
            c.drawString(155*mm, y - 3.5*mm, "Total")
            
            c.setFillColor(colors.black)
            y -= 10*mm
            
            total_general = 0
            c.setFont("Helvetica", 9)
            
            for item in items:
                price_unit = item['price']
                price_remise = price_unit * (1 - item['discount']/100)
                total_ligne = price_remise * item['quantity']
                total_general += total_ligne
                
                c.drawString(22*mm, y, item['product_name'][:35])
                c.drawString(92*mm, y, str(item['quantity']))
                c.drawString(105*mm, y, format_price(price_unit))
                c.drawString(132*mm, y, f"{item['discount']}%")
                c.drawString(155*mm, y, format_price(total_ligne))
                
                y -= 5*mm
            
            # Ligne séparatrice
            y -= 2*mm
            c.setStrokeColor(colors.grey)
            c.setLineWidth(0.5)
            c.line(20*mm, y, width - 20*mm, y)
            
            # Totaux
            y -= 6*mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(130*mm, y, "Total dépôt:")
            c.drawString(155*mm, y, format_price(total_general))
            
            if commission > 0:
                y -= 5*mm
                c.setFont("Helvetica", 9)
                c.drawString(130*mm, y, f"Commission ({commission}%):")
                c.drawString(155*mm, y, format_price(total_general * commission / 100))
            
            # Conditions
            y -= 12*mm
            c.setFont("Helvetica-Bold", 9)
            c.drawString(20*mm, y, "CONDITIONS:")
            c.setFont("Helvetica", 8)
            y -= 4*mm
            conditions = [
                f"• Commission sur ventes: {commission}%",
                "• Les produits restent la propriété de KRYSTO jusqu'à la vente",
                "• Règlement des ventes: à définir entre les parties",
                "• Retour des invendus sur demande de KRYSTO"
            ]
            for cond in conditions:
                c.drawString(20*mm, y, cond)
                y -= 3.5*mm
            
            # Signatures
            y -= 8*mm
            c.setFont("Helvetica-Bold", 9)
            c.drawString(20*mm, y, "KRYSTO")
            c.drawString(120*mm, y, "LE DÉPOSITAIRE")
            
            y -= 3*mm
            c.setFont("Helvetica", 8)
            c.drawString(20*mm, y, "Signature:")
            c.drawString(120*mm, y, "Signature:")
            
            # Cadres signature
            c.setStrokeColor(colors.grey)
            c.rect(20*mm, y - 18*mm, 60*mm, 15*mm, stroke=True, fill=False)
            c.rect(120*mm, y - 18*mm, 60*mm, 15*mm, stroke=True, fill=False)
            
            return y - 25*mm
        
        # Premier exemplaire
        draw_receipt(0, "Exemplaire KRYSTO")
        
        # Ligne de découpe
        c.setStrokeColor(colors.grey)
        c.setDash(3, 3)
        c.line(10*mm, height/2, width - 10*mm, height/2)
        c.setFont("Helvetica", 7)
        c.drawString(width/2 - 15*mm, height/2 + 2*mm, "✂ DÉCOUPER ICI")
        c.setDash()
        
        # Deuxième exemplaire
        draw_receipt(height/2, "Exemplaire Dépositaire")
        
        c.save()
        return filepath
        
    except ImportError:
        messagebox.showerror("Erreur", "Module reportlab non installé.\nInstallez-le avec: pip install reportlab")
        return None
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur génération PDF: {str(e)}")
        return None


class NewProductsEmailDialog(ctk.CTkToplevel):
    """Dialogue pour sélectionner les produits à proposer par email."""
    def __init__(self, parent, depot):
        super().__init__(parent)
        self.depot = depot
        self.title("Proposer des produits")
        self.geometry("550x550")
        self.transient(parent)
        self.grab_set()
        self.selected_products = []
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        client_name = self.depot['client_name'] if 'client_name' in self.depot.keys() else "Client"
        ctk.CTkLabel(main, text=f"🎉 Proposer à: {client_name}", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 15))
        
        ctk.CTkLabel(main, text="Sélectionnez les produits à proposer:").pack(anchor="w")
        
        # Liste des produits avec checkboxes
        self.products_frame = ctk.CTkScrollableFrame(main, height=300, fg_color="#1a1a1a")
        self.products_frame.pack(fill="both", expand=True, pady=10)
        
        products = get_all_products()
        self.product_vars = {}
        
        for p in products:
            product_id = p['id']
            name = p['name'] if 'name' in p.keys() else "Produit"
            price = p['price'] if 'price' in p.keys() else 0
            image_url = p['image_url'] if 'image_url' in p.keys() and p['image_url'] else None
            
            row = ctk.CTkFrame(self.products_frame, fg_color="#2a2a2a")
            row.pack(fill="x", pady=2, padx=5)
            
            var = ctk.BooleanVar(value=False)
            self.product_vars[product_id] = (var, p)
            
            ctk.CTkCheckBox(row, text="", variable=var, width=30).pack(side="left", padx=5)
            
            # Indicateur photo
            if image_url:
                ctk.CTkLabel(row, text="🖼️", font=("Helvetica", 10)).pack(side="left")
            
            ctk.CTkLabel(row, text=name, font=("Helvetica", 11)).pack(side="left", padx=5, pady=8)
            ctk.CTkLabel(row, text=format_price(price), text_color=KRYSTO_SECONDARY,
                         font=("Helvetica", 11)).pack(side="right", padx=10)
        
        # Info catalogue
        catalog_url = get_catalog_url()
        if catalog_url:
            ctk.CTkLabel(main, text="✅ Le lien du catalogue sera inclus automatiquement",
                         text_color=KRYSTO_SECONDARY, font=("Helvetica", 10)).pack(anchor="w", pady=5)
        else:
            ctk.CTkLabel(main, text="💡 Ajoutez un lien catalogue dans Paramètres > Catalogue",
                         text_color="#888", font=("Helvetica", 10)).pack(anchor="w", pady=5)
        
        # Boutons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="📧 Envoyer", fg_color=KRYSTO_PRIMARY, command=self._send).pack(side="left", expand=True, padx=5)
    
    def _send(self):
        # Récupérer les produits sélectionnés AVEC leurs images
        selected = []
        for pid, (var, product) in self.product_vars.items():
            if var.get():
                selected.append({
                    'name': product['name'] if 'name' in product.keys() else '',
                    'description': product['description'] if 'description' in product.keys() else '',
                    'price': product['price'] if 'price' in product.keys() else 0,
                    'image_url': product['image_url'] if 'image_url' in product.keys() else None,
                })
        
        if not selected:
            messagebox.showwarning("Attention", "Sélectionnez au moins un produit")
            return
        
        success, msg = send_depot_email(self.depot['id'], "new_products", selected)
        if success:
            messagebox.showinfo("Succès", f"Email envoyé avec {len(selected)} produit(s)!")
            self.destroy()
        else:
            messagebox.showerror("Erreur", msg)


# ============================================================================
# FRAMES UI - MAILING
# ============================================================================
class MailingFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.designer = EmailDesigner()
        self.selected_block_idx = None
        self.selected_group_id = None  # Groupe sélectionné pour les destinataires
        self._group_id_map = {}  # Mapping nom groupe -> id
        self._create_ui()
    
    def _create_ui(self):
        header = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="📧 Mailing", font=("Helvetica", 20, "bold")).pack(side="left", padx=20, pady=15)
        ctk.CTkButton(header, text="⚙️ SMTP", width=90, fg_color="gray",
                      command=lambda: SMTPConfigDialog(self)).pack(side="right", padx=5, pady=10)
        ctk.CTkButton(header, text="📚 Catalogue", width=100, fg_color=KRYSTO_PRIMARY,
                      command=lambda: SettingsDialog(self)).pack(side="right", padx=5, pady=10)
        
        self.tabs = ctk.CTkTabview(self, fg_color=KRYSTO_DARK)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tabs.add("✏️ Éditeur")
        self.tabs.add("📋 Templates")
        self.tabs.add("👥 Groupes")
        self.tabs.add("📨 Destinataires")
        self.tabs.add("📤 Envoi")
        
        self._create_editor_tab(self.tabs.tab("✏️ Éditeur"))
        self._create_templates_tab(self.tabs.tab("📋 Templates"))
        self._create_groups_tab(self.tabs.tab("👥 Groupes"))
        self._create_recipients_tab(self.tabs.tab("📨 Destinataires"))
        self._create_send_tab(self.tabs.tab("📤 Envoi"))
    
    def _create_editor_tab(self, parent):
        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Gauche - Blocs (plus large pour les nouveaux blocs)
        left = ctk.CTkFrame(main, width=200, fg_color=KRYSTO_DARK)
        left.pack(side="left", fill="y", padx=(0, 5))
        left.pack_propagate(False)
        
        # Header avec bouton template rapide
        left_header = ctk.CTkFrame(left, fg_color="transparent")
        left_header.pack(fill="x", padx=5, pady=10)
        ctk.CTkLabel(left_header, text="📦 Blocs", font=("Helvetica", 12, "bold")).pack(side="left")
        ctk.CTkButton(left_header, text="🚀", width=30, fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK,
                      command=self._show_quick_templates).pack(side="right")
        
        blocks_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        blocks_scroll.pack(fill="both", expand=True, padx=5)
        
        # Utiliser les catégories définies
        for cat, block_types in BLOCK_CATEGORIES.items():
            ctk.CTkLabel(blocks_scroll, text=cat, font=("Helvetica", 10, "bold"), 
                         text_color=KRYSTO_SECONDARY).pack(anchor="w", pady=(10, 3))
            for bt in block_types:
                if bt in BLOCK_TYPES:
                    block_class = BLOCK_TYPES[bt]
                    label = f"{block_class.BLOCK_ICON} {block_class.BLOCK_NAME}"
                    ctk.CTkButton(blocks_scroll, text=label, anchor="w", fg_color="#2a2a2a", 
                                  hover_color=KRYSTO_PRIMARY, height=28,
                                  command=lambda b=bt: self._add_block(b)).pack(fill="x", pady=1)
        
        # Centre - Structure
        center = ctk.CTkFrame(main, width=280, fg_color=KRYSTO_DARK)
        center.pack(side="left", fill="y", padx=5)
        center.pack_propagate(False)
        
        ctk.CTkLabel(center, text="📋 Structure", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        self.blocks_list = ctk.CTkScrollableFrame(center, fg_color="#1a1a1a")
        self.blocks_list.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        
        actions = ctk.CTkFrame(center, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=10)
        for txt, cmd, color in [("⬆️", lambda: self._move_block(-1), "gray"), 
                                 ("⬇️", lambda: self._move_block(1), "gray"),
                                 ("📋", self._duplicate_block, "gray"), 
                                 ("✏️", self._edit_selected, KRYSTO_PRIMARY), 
                                 ("🗑️", self._delete_selected, "#dc3545")]:
            ctk.CTkButton(actions, text=txt, width=40, fg_color=color,
                          command=cmd).pack(side="left", padx=2)
        
        # Droite - Paramètres
        right = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        right.pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        settings = ctk.CTkFrame(right, fg_color="transparent")
        settings.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(settings, text="⚙️ Paramètres", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        for label, attr, placeholder in [("Sujet:", "subject_entry", "Sujet de l'email"),
                                          ("Preheader:", "preheader_entry", "Texte d'aperçu"),
                                          ("Titre:", "header_title", COMPANY_NAME)]:
            row = ctk.CTkFrame(settings, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=label, width=70).pack(side="left")
            entry = ctk.CTkEntry(row, height=32, placeholder_text=placeholder)
            entry.pack(side="left", fill="x", expand=True)
            setattr(self, attr, entry)
        
        self.header_title.insert(0, COMPANY_NAME)
        
        row_style = ctk.CTkFrame(settings, fg_color="transparent")
        row_style.pack(fill="x", pady=5)
        ctk.CTkLabel(row_style, text="En-tête:", width=70).pack(side="left")
        self.header_style = ctk.CTkSegmentedButton(row_style, values=["gradient", "simple", "minimal", "none"], width=220)
        self.header_style.pack(side="left")
        self.header_style.set("gradient")
        
        action_btns = ctk.CTkFrame(right, fg_color="transparent")
        action_btns.pack(fill="x", padx=15, pady=10)
        ctk.CTkButton(action_btns, text="👁️ Aperçu", fg_color=KRYSTO_PRIMARY, command=self._preview).pack(side="left", padx=3)
        ctk.CTkButton(action_btns, text="💾 Sauver", fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK,
                      command=self._save_template).pack(side="left", padx=3)
        ctk.CTkButton(action_btns, text="📧 Test", fg_color="gray", command=self._send_test).pack(side="left", padx=3)
        ctk.CTkButton(action_btns, text="🗑️ Vider", fg_color="#dc3545", command=self._clear_all).pack(side="left", padx=3)
        
        # Bouton ENVOYER prominent
        send_frame = ctk.CTkFrame(right, fg_color="transparent")
        send_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(send_frame, text="🚀 ENVOYER CAMPAGNE", height=45, font=("Helvetica", 13, "bold"),
                      fg_color="#28a745", hover_color="#218838", command=self._go_to_send_tab).pack(fill="x")
        
        # Variables
        info = ctk.CTkFrame(right, fg_color="#1a1a1a")
        info.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        ctk.CTkLabel(info, text="📝 Variables disponibles:", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        vars_text = "{{name}} - Nom client\n{{email}} - Email\n{{date}} - Date du jour\n{{code_parrainage}} - Code unique\n{{catalog_url}} - Lien catalogue\n{{dette_m1}} - Dette M1\n{{dette_m2}} - Dette M2\n{{dette_m3}} - Dette M3\n{{dette_m3plus}} - Dette M3+\n{{dette_total}} - Total dettes"
        ctk.CTkLabel(info, text=vars_text, text_color="#888", font=("Courier", 10), justify="left").pack(anchor="w", padx=10)
        
        self._refresh_blocks_list()
    
    def _clear_all(self):
        if messagebox.askyesno("Confirmation", "Supprimer tous les blocs ?"):
            self.designer.clear_blocks()
            self.selected_block_idx = None
            self._refresh_blocks_list()
    
    def _go_to_send_tab(self):
        """Navigue vers l'onglet d'envoi avec vérifications."""
        if not self.subject_entry.get():
            messagebox.showwarning("Attention", "Définissez un sujet d'abord!")
            return
        if not self.designer.blocks:
            messagebox.showwarning("Attention", "Ajoutez du contenu à votre email!")
            return
        self._update_settings()
        self._update_summary()
        self.tabs.set("📤 Envoi")
    
    def _create_templates_tab(self, parent):
        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Section Templates prédéfinis
        predefined_section = ctk.CTkFrame(main, fg_color=KRYSTO_DARK, corner_radius=10)
        predefined_section.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(predefined_section, text="🚀 Démarrage Rapide", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 10))
        ctk.CTkLabel(predefined_section, text="Choisissez un template pour commencer rapidement", 
                     text_color="#888", font=("Helvetica", 10)).pack(anchor="w", padx=15)
        
        templates_grid = ctk.CTkFrame(predefined_section, fg_color="transparent")
        templates_grid.pack(fill="x", padx=15, pady=15)
        
        for i, (key, tmpl) in enumerate(EMAIL_TEMPLATES.items()):
            if key == "blank": continue
            btn = ctk.CTkButton(templates_grid, text=tmpl['name'], width=130, height=60,
                               fg_color="#2a2a2a", hover_color=KRYSTO_PRIMARY,
                               command=lambda k=key: self._load_predefined_template(k))
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)
        
        # Séparateur
        ctk.CTkFrame(main, height=2, fg_color="#333").pack(fill="x", pady=10)
        
        # Section Mes templates
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="📋 Mes Templates Sauvegardés", font=("Helvetica", 14, "bold")).pack(side="left")
        
        # Filtre par type
        self.template_type_filter = ctk.CTkSegmentedButton(header, values=["Tous", "Marketing", "Rappel"], 
                                                            command=self._load_templates)
        self.template_type_filter.pack(side="right")
        self.template_type_filter.set("Tous")
        
        self.templates_list = ctk.CTkScrollableFrame(main, fg_color="#1a1a1a")
        self.templates_list.pack(fill="both", expand=True)
        self._load_templates()
    
    def _load_predefined_template(self, template_key):
        """Charge un template prédéfini."""
        if template_key not in EMAIL_TEMPLATES:
            return
        
        tmpl = EMAIL_TEMPLATES[template_key]
        
        if self.designer.blocks:
            if not messagebox.askyesno("Confirmation", "Remplacer les blocs actuels ?"):
                return
        
        self.designer.clear_blocks()
        
        for block_data in tmpl.get('blocks', []):
            block_type = block_data.get('type')
            if block_type in BLOCK_TYPES:
                block_class = BLOCK_TYPES[block_type]
                default_content = block_class.get_default_content()
                content = {**default_content, **block_data.get('content', {})}
                self.designer.add_block(block_class(content))
        
        self._refresh_blocks_list()
        self.tabs.set("✏️ Éditeur")
        messagebox.showinfo("Template chargé", f"Template '{tmpl['name']}' chargé avec {len(tmpl.get('blocks', []))} blocs!")
    
    def _create_groups_tab(self, parent):
        """Onglet de gestion des groupes de clients."""
        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Header avec bouton d'ajout
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="👥 Groupes de destinataires", font=("Helvetica", 14, "bold")).pack(side="left")
        ctk.CTkButton(header, text="➕ Nouveau groupe", fg_color=KRYSTO_PRIMARY,
                      command=self._add_group).pack(side="right")
        
        # Liste des groupes
        self.groups_list = ctk.CTkScrollableFrame(main, fg_color="#1a1a1a")
        self.groups_list.pack(fill="both", expand=True)
        self._load_groups()
    
    def _load_groups(self):
        """Charge la liste des groupes."""
        for w in self.groups_list.winfo_children(): w.destroy()
        
        groups = get_all_client_groups()
        if not groups:
            ctk.CTkLabel(self.groups_list, text="Aucun groupe créé", text_color="#666").pack(pady=30)
            ctk.CTkLabel(self.groups_list, text="Créez des groupes pour organiser vos destinataires\net envoyer des campagnes ciblées", 
                         text_color="#555", font=("Helvetica", 10)).pack()
            return
        
        for g in groups:
            gid = g['id']
            name = g['name']
            desc = g['description'] if 'description' in g.keys() else ""
            color = g['color'] if 'color' in g.keys() else KRYSTO_PRIMARY
            member_count = get_group_member_count(gid)
            
            frame = ctk.CTkFrame(self.groups_list, fg_color="#2a2a2a")
            frame.pack(fill="x", pady=3, padx=5)
            
            # Indicateur couleur
            ctk.CTkFrame(frame, width=8, fg_color=color, corner_radius=0).pack(side="left", fill="y")
            
            # Info groupe
            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
            
            row1 = ctk.CTkFrame(info, fg_color="transparent")
            row1.pack(fill="x")
            ctk.CTkLabel(row1, text=name, font=("Helvetica", 12, "bold")).pack(side="left")
            ctk.CTkLabel(row1, text=f"({member_count} membre{'s' if member_count > 1 else ''})", 
                         text_color=KRYSTO_SECONDARY, font=("Helvetica", 10)).pack(side="left", padx=10)
            
            if desc:
                ctk.CTkLabel(info, text=desc, text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
            
            # Boutons
            btns = ctk.CTkFrame(frame, fg_color="transparent")
            btns.pack(side="right", padx=10)
            ctk.CTkButton(btns, text="👥", width=35, fg_color=KRYSTO_PRIMARY, 
                          command=lambda g=gid: self._manage_group_members(g)).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="✏️", width=35, fg_color="gray",
                          command=lambda g=gid: self._edit_group(g)).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                          command=lambda g=gid, n=name: self._delete_group(g, n)).pack(side="left", padx=2)
    
    def _add_group(self):
        """Ajoute un nouveau groupe."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("➕ Nouveau groupe")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Créer un groupe", font=("Helvetica", 14, "bold")).pack(pady=15)
        
        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="x", padx=20)
        
        ctk.CTkLabel(container, text="Nom du groupe:").pack(anchor="w")
        name_entry = ctk.CTkEntry(container, placeholder_text="Ex: Clients VIP")
        name_entry.pack(fill="x", pady=5)
        
        ctk.CTkLabel(container, text="Description (optionnelle):").pack(anchor="w")
        desc_entry = ctk.CTkEntry(container, placeholder_text="Ex: Meilleurs clients")
        desc_entry.pack(fill="x", pady=5)
        
        ctk.CTkLabel(container, text="Couleur:").pack(anchor="w")
        colors = [KRYSTO_PRIMARY, KRYSTO_SECONDARY, "#ff6b6b", "#4ecdc4", "#45b7d1", "#f9ca24", "#6c5ce7", "#fd79a8"]
        color_var = ctk.StringVar(value=KRYSTO_PRIMARY)
        
        colors_frame = ctk.CTkFrame(container, fg_color="transparent")
        colors_frame.pack(fill="x", pady=5)
        for c in colors:
            btn = ctk.CTkButton(colors_frame, text="", width=30, height=30, fg_color=c, hover_color=c,
                               command=lambda col=c: color_var.set(col))
            btn.pack(side="left", padx=3)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Attention", "Entrez un nom")
                return
            save_client_group(name, desc_entry.get().strip(), color_var.get())
            self._load_groups()
            dialog.destroy()
            messagebox.showinfo("OK", f"Groupe '{name}' créé!")
        
        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(pady=20)
        ctk.CTkButton(btns, text="Annuler", fg_color="gray", command=dialog.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Créer", fg_color=KRYSTO_PRIMARY, command=save).pack(side="left", padx=10)
    
    def _edit_group(self, group_id):
        """Édite un groupe existant."""
        group = get_client_group(group_id)
        if not group: return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("✏️ Modifier groupe")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Modifier le groupe", font=("Helvetica", 14, "bold")).pack(pady=15)
        
        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="x", padx=20)
        
        ctk.CTkLabel(container, text="Nom du groupe:").pack(anchor="w")
        name_entry = ctk.CTkEntry(container)
        name_entry.pack(fill="x", pady=5)
        name_entry.insert(0, group['name'])
        
        ctk.CTkLabel(container, text="Description:").pack(anchor="w")
        desc_entry = ctk.CTkEntry(container)
        desc_entry.pack(fill="x", pady=5)
        desc_entry.insert(0, group['description'] if 'description' in group.keys() else "")
        
        ctk.CTkLabel(container, text="Couleur:").pack(anchor="w")
        colors = [KRYSTO_PRIMARY, KRYSTO_SECONDARY, "#ff6b6b", "#4ecdc4", "#45b7d1", "#f9ca24", "#6c5ce7", "#fd79a8"]
        current_color = group['color'] if 'color' in group.keys() else KRYSTO_PRIMARY
        color_var = ctk.StringVar(value=current_color)
        
        colors_frame = ctk.CTkFrame(container, fg_color="transparent")
        colors_frame.pack(fill="x", pady=5)
        for c in colors:
            btn = ctk.CTkButton(colors_frame, text="", width=30, height=30, fg_color=c, hover_color=c,
                               command=lambda col=c: color_var.set(col))
            btn.pack(side="left", padx=3)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Attention", "Entrez un nom")
                return
            save_client_group(name, desc_entry.get().strip(), color_var.get(), group_id)
            self._load_groups()
            dialog.destroy()
        
        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(pady=20)
        ctk.CTkButton(btns, text="Annuler", fg_color="gray", command=dialog.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Sauvegarder", fg_color=KRYSTO_PRIMARY, command=save).pack(side="left", padx=10)
    
    def _delete_group(self, group_id, name):
        """Supprime un groupe."""
        if messagebox.askyesno("Confirmation", f"Supprimer le groupe '{name}' ?"):
            delete_client_group(group_id)
            self._load_groups()
    
    def _manage_group_members(self, group_id):
        """Gère les membres d'un groupe."""
        group = get_client_group(group_id)
        if not group: return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"👥 Membres: {group['name']}")
        dialog.geometry("700x550")
        dialog.transient(self)
        dialog.grab_set()
        
        # Header
        header = ctk.CTkFrame(dialog, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(header, text=f"Gestion des membres - {group['name']}", 
                     font=("Helvetica", 14, "bold")).pack(side="left")
        
        # Contenu principal en 2 colonnes
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Colonne gauche - Membres actuels
        left = ctk.CTkFrame(content, fg_color=KRYSTO_DARK)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ctk.CTkLabel(left, text="✓ Membres du groupe", font=("Helvetica", 11, "bold")).pack(pady=10)
        members_list = ctk.CTkScrollableFrame(left, fg_color="#1a1a1a")
        members_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Colonne droite - Clients disponibles
        right = ctk.CTkFrame(content, fg_color=KRYSTO_DARK)
        right.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        ctk.CTkLabel(right, text="➕ Ajouter des clients", font=("Helvetica", 11, "bold")).pack(pady=10)
        
        # Filtre
        filter_frame = ctk.CTkFrame(right, fg_color="transparent")
        filter_frame.pack(fill="x", padx=10)
        search_var = ctk.StringVar()
        ctk.CTkEntry(filter_frame, textvariable=search_var, placeholder_text="🔍 Rechercher...").pack(fill="x")
        
        available_list = ctk.CTkScrollableFrame(right, fg_color="#1a1a1a")
        available_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        member_ids = set()
        
        def refresh_lists():
            nonlocal member_ids
            # Vider les listes
            for w in members_list.winfo_children(): w.destroy()
            for w in available_list.winfo_children(): w.destroy()
            
            # Membres actuels
            members = get_group_members(group_id)
            member_ids = {m['id'] for m in members}
            
            if not members:
                ctk.CTkLabel(members_list, text="Aucun membre", text_color="#666").pack(pady=20)
            else:
                for m in members:
                    frame = ctk.CTkFrame(members_list, fg_color="#2a2a2a")
                    frame.pack(fill="x", pady=1)
                    ctk.CTkLabel(frame, text=m['name'], font=("Helvetica", 10)).pack(side="left", padx=10, pady=5)
                    email = m['email'] if 'email' in m.keys() else ""
                    if email:
                        ctk.CTkLabel(frame, text=email, text_color="#888", font=("Helvetica", 9)).pack(side="left")
                    ctk.CTkButton(frame, text="✕", width=25, height=25, fg_color="#dc3545",
                                  command=lambda mid=m['id']: (remove_client_from_group(mid, group_id), refresh_lists())).pack(side="right", padx=5, pady=3)
            
            # Clients disponibles
            all_clients = get_all_clients()
            search = search_var.get().lower()
            available = [c for c in all_clients if c['id'] not in member_ids 
                        and c['email']  # Seulement ceux avec email
                        and (not search or search in c['name'].lower())]
            
            if not available:
                ctk.CTkLabel(available_list, text="Tous les clients sont déjà membres\nou n'ont pas d'email", text_color="#666").pack(pady=20)
            else:
                for c in available[:50]:  # Limiter à 50
                    frame = ctk.CTkFrame(available_list, fg_color="#2a2a2a")
                    frame.pack(fill="x", pady=1)
                    ctk.CTkLabel(frame, text=c['name'], font=("Helvetica", 10)).pack(side="left", padx=10, pady=5)
                    email = c['email'] if 'email' in c.keys() else ""
                    if email:
                        ctk.CTkLabel(frame, text=email, text_color="#888", font=("Helvetica", 9)).pack(side="left")
                    ctk.CTkButton(frame, text="➕", width=25, height=25, fg_color=KRYSTO_PRIMARY,
                                  command=lambda cid=c['id']: (add_client_to_group(cid, group_id), refresh_lists())).pack(side="right", padx=5, pady=3)
        
        search_var.trace_add("write", lambda *args: refresh_lists())
        refresh_lists()
        
        # Boutons en bas
        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(pady=15)
        
        def add_all_newsletter():
            clients = get_all_clients(newsletter_only=True)
            client_ids = [c['id'] for c in clients if c['email']]
            add_multiple_clients_to_group(client_ids, group_id)
            refresh_lists()
            messagebox.showinfo("OK", f"{len(client_ids)} clients newsletter ajoutés!")
        
        ctk.CTkButton(btns, text="📧 Ajouter tous Newsletter", fg_color="gray",
                      command=add_all_newsletter).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Fermer", fg_color=KRYSTO_PRIMARY, 
                      command=lambda: (self._load_groups(), dialog.destroy())).pack(side="left", padx=5)
    
    def _create_recipients_tab(self, parent):
        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Section filtres
        filter_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        filter_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(filter_frame, text="Filtre rapide:").pack(side="left", padx=15, pady=10)
        self.recipient_filter = ctk.CTkSegmentedButton(filter_frame, 
            values=["Newsletter", "Pro", "Pro dette", "Particulier", "Prospect", "Groupe"],
            command=self._filter_recipients)
        self.recipient_filter.pack(side="left", padx=10, pady=10)
        self.recipient_filter.set("Newsletter")
        
        # Sélecteur de groupe (visible uniquement quand "Groupe" est sélectionné)
        self.group_selector_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        
        ctk.CTkLabel(self.group_selector_frame, text="Groupe:").pack(side="left", padx=(0, 5))
        self.group_combo = ctk.CTkComboBox(self.group_selector_frame, values=[""], width=200,
                                           command=self._on_group_selected)
        self.group_combo.pack(side="left")
        
        self.recipients_count = ctk.CTkLabel(filter_frame, text="0 destinataire(s)", text_color=KRYSTO_SECONDARY)
        self.recipients_count.pack(side="right", padx=15)
        
        # Liste des destinataires
        self.recipients_list = ctk.CTkScrollableFrame(main, fg_color="#1a1a1a")
        self.recipients_list.pack(fill="both", expand=True)
        
        self._refresh_group_combo()
        self._filter_recipients("Newsletter")
    
    def _refresh_group_combo(self):
        """Met à jour la liste des groupes dans le combo."""
        groups = get_all_client_groups()
        group_names = [f"{g['name']} ({get_group_member_count(g['id'])})" for g in groups]
        self.group_combo.configure(values=group_names if group_names else ["Aucun groupe"])
        self._group_id_map = {f"{g['name']} ({get_group_member_count(g['id'])})": g['id'] for g in groups}
        if group_names:
            self.group_combo.set(group_names[0])
    
    def _on_group_selected(self, value):
        """Appelé quand un groupe est sélectionné."""
        if value in self._group_id_map:
            self.selected_group_id = self._group_id_map[value]
            self._filter_recipients("Groupe")
    
    def _create_send_tab(self, parent):
        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        summary = ctk.CTkFrame(main, fg_color=KRYSTO_DARK)
        summary.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(summary, text="📤 Résumé", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=20, pady=10)
        self.summary_subject = ctk.CTkLabel(summary, text="Sujet: (non défini)", text_color="#888")
        self.summary_subject.pack(anchor="w", padx=20)
        self.summary_blocks = ctk.CTkLabel(summary, text="Blocs: 0", text_color="#888")
        self.summary_blocks.pack(anchor="w", padx=20)
        self.summary_recipients = ctk.CTkLabel(summary, text="Destinataires: 0", text_color="#888")
        self.summary_recipients.pack(anchor="w", padx=20, pady=(0, 10))
        
        self.send_btn = ctk.CTkButton(main, text="🚀 ENVOYER", height=45, font=("Helvetica", 14, "bold"),
                                       fg_color=KRYSTO_PRIMARY, command=self._send_campaign)
        self.send_btn.pack(fill="x")
        
        self.progress_frame = ctk.CTkFrame(main, fg_color="#1a1a1a")
        self.progress_frame.pack(fill="both", expand=True, pady=15)
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=400)
        self.progress_bar.pack(pady=20)
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Prêt")
        self.progress_label.pack()
        
        self.progress_log = ctk.CTkTextbox(self.progress_frame, height=150)
        self.progress_log.pack(fill="x", padx=15, pady=15)
    
    def _add_block(self, block_type):
        BlockEditorDialog(self, block_type, on_save=lambda b: (self.designer.add_block(b), self._refresh_blocks_list()))
    
    def _show_quick_templates(self):
        """Affiche une popup de sélection rapide de templates."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("🚀 Templates Rapides")
        dialog.geometry("550x450")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Choisissez un template pour commencer", 
                     font=("Helvetica", 14, "bold")).pack(pady=15)
        
        container = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=10)
        
        for key, tmpl in EMAIL_TEMPLATES.items():
            if key == "blank": continue
            
            frame = ctk.CTkFrame(container, fg_color="#2a2a2a", corner_radius=10)
            frame.pack(fill="x", pady=5)
            
            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=15, pady=12)
            
            ctk.CTkLabel(info, text=tmpl['name'], font=("Helvetica", 13, "bold")).pack(anchor="w")
            ctk.CTkLabel(info, text=tmpl.get('description', ''), text_color="#888", 
                         font=("Helvetica", 10)).pack(anchor="w")
            ctk.CTkLabel(info, text=f"{len(tmpl.get('blocks', []))} blocs", text_color=KRYSTO_SECONDARY,
                         font=("Helvetica", 9)).pack(anchor="w")
            
            ctk.CTkButton(frame, text="Utiliser", width=80, fg_color=KRYSTO_PRIMARY,
                          command=lambda k=key, d=dialog: self._apply_quick_template(k, d)).pack(side="right", padx=15)
        
        ctk.CTkButton(dialog, text="Annuler", fg_color="gray", 
                      command=dialog.destroy).pack(pady=15)
    
    def _apply_quick_template(self, template_key, dialog):
        """Applique un template rapide."""
        if self.designer.blocks:
            if not messagebox.askyesno("Confirmation", "Remplacer les blocs actuels ?"):
                return
        
        self._load_predefined_template(template_key)
        dialog.destroy()
    
    def _refresh_blocks_list(self):
        for w in self.blocks_list.winfo_children(): w.destroy()
        if not self.designer.blocks:
            ctk.CTkLabel(self.blocks_list, text="Aucun bloc", text_color="#666").pack(pady=30)
            return
        for i, b in enumerate(self.designer.blocks):
            fg = KRYSTO_PRIMARY if i == self.selected_block_idx else "#2a2a2a"
            frame = ctk.CTkFrame(self.blocks_list, fg_color=fg)
            frame.pack(fill="x", pady=1, padx=3)
            ctk.CTkLabel(frame, text=b.get_preview_text(), anchor="w", font=("Helvetica", 10)).pack(side="left", padx=8, pady=5)
            frame.bind("<Button-1>", lambda e, idx=i: self._select_block(idx))
            for child in frame.winfo_children(): child.bind("<Button-1>", lambda e, idx=i: self._select_block(idx))
    
    def _select_block(self, idx):
        self.selected_block_idx = idx
        self._refresh_blocks_list()
    
    def _move_block(self, direction):
        if self.selected_block_idx is None: return
        new_idx = self.selected_block_idx + direction
        if 0 <= new_idx < len(self.designer.blocks):
            self.designer.move_block(self.selected_block_idx, new_idx)
            self.selected_block_idx = new_idx
            self._refresh_blocks_list()
    
    def _duplicate_block(self):
        if self.selected_block_idx is not None:
            new_idx = self.designer.duplicate_block(self.selected_block_idx)
            if new_idx >= 0: self.selected_block_idx = new_idx; self._refresh_blocks_list()
    
    def _edit_selected(self):
        if self.selected_block_idx is None: return
        block = self.designer.blocks[self.selected_block_idx]
        def on_save(new_block):
            self.designer.blocks[self.selected_block_idx] = new_block
            self._refresh_blocks_list()
        BlockEditorDialog(self, block.BLOCK_TYPE, existing_block=block, on_save=on_save)
    
    def _delete_selected(self):
        if self.selected_block_idx is not None:
            self.designer.remove_block(self.selected_block_idx)
            self.selected_block_idx = None
            self._refresh_blocks_list()
    
    def _update_settings(self):
        self.designer.settings['header_style'] = self.header_style.get()
        self.designer.settings['header_title'] = self.header_title.get()
        self.designer.settings['preheader'] = self.preheader_entry.get()
    
    def _preview(self):
        self._update_settings()
        self.designer.preview_in_browser()
    
    def _save_template(self):
        name = self.header_title.get() or "Sans nom"
        subject = self.subject_entry.get() or "Sans sujet"
        
        # Demander le type
        ttype = "marketing"
        if "rappel" in name.lower() or "dette" in name.lower() or "impayé" in name.lower():
            ttype = "rappel"
        
        self._update_settings()
        design_json = json.dumps(self.designer.to_dict())
        save_email_template(name, subject, design_json, ttype)
        messagebox.showinfo("Succès", "Template sauvegardé!")
        self._load_templates()
    
    def _load_templates(self, filter_val=None):
        for w in self.templates_list.winfo_children(): w.destroy()
        
        f = self.template_type_filter.get() if hasattr(self, 'template_type_filter') else "Tous"
        ttype = None
        if f == "Marketing": ttype = "marketing"
        elif f == "Rappel": ttype = "rappel"
        
        templates = get_email_templates(ttype)
        if not templates:
            ctk.CTkLabel(self.templates_list, text="Aucun template", text_color="#666").pack(pady=30)
            return
        
        for t in templates:
            frame = ctk.CTkFrame(self.templates_list, fg_color="#2a2a2a")
            frame.pack(fill="x", pady=2, padx=5)
            info = ctk.CTkFrame(frame, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=10, pady=8)
            
            name = t['name'] if 'name' in t.keys() else "Sans nom"
            ttype_display = t['template_type'] if 'template_type' in t.keys() else "marketing"
            badge_color = "#ff6b6b" if ttype_display == "rappel" else KRYSTO_SECONDARY
            
            row = ctk.CTkFrame(info, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(row, text=name, font=("Helvetica", 12, "bold")).pack(side="left")
            ctk.CTkLabel(row, text=ttype_display.upper(), text_color=badge_color, 
                         font=("Helvetica", 9, "bold")).pack(side="left", padx=10)
            
            subject = t['subject'] if 'subject' in t.keys() else ""
            ctk.CTkLabel(info, text=f"Sujet: {subject}", text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
            
            btns = ctk.CTkFrame(frame, fg_color="transparent")
            btns.pack(side="right", padx=10)
            ctk.CTkButton(btns, text="📂", width=35, fg_color=KRYSTO_PRIMARY,
                          command=lambda tmpl=t: self._load_template(tmpl)).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                          command=lambda tmpl=t: self._delete_template(tmpl)).pack(side="left", padx=2)
    
    def _load_template(self, template):
        try:
            data = json.loads(template['design_json'])
            self.designer.from_dict(data)
            self.subject_entry.delete(0, "end")
            self.subject_entry.insert(0, template['subject'] if 'subject' in template.keys() else '')
            self.header_title.delete(0, "end")
            self.header_title.insert(0, self.designer.settings.get('header_title', COMPANY_NAME))
            self.header_style.set(self.designer.settings.get('header_style', 'gradient'))
            self.preheader_entry.delete(0, "end")
            self.preheader_entry.insert(0, self.designer.settings.get('preheader', ''))
            self._refresh_blocks_list()
            self.tabs.set("✏️ Éditeur")
            messagebox.showinfo("OK", "Template chargé!")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
    
    def _delete_template(self, template):
        name = template['name'] if 'name' in template.keys() else "ce template"
        if messagebox.askyesno("Confirmation", f"Supprimer '{name}' ?"):
            delete_email_template(template['id'])
            self._load_templates()
    
    def _filter_recipients(self, filter_type):
        for w in self.recipients_list.winfo_children(): w.destroy()
        
        # Afficher/masquer le sélecteur de groupe
        if filter_type == "Groupe":
            self.group_selector_frame.pack(side="left", padx=10)
            self._refresh_group_combo()
            if self.selected_group_id:
                clients = get_group_members(self.selected_group_id)
            else:
                clients = []
        else:
            self.group_selector_frame.pack_forget()
            if filter_type == "Newsletter": 
                clients = get_all_clients(newsletter_only=True)
            elif filter_type == "Pro": 
                clients = get_all_clients(client_type="professionnel")
            elif filter_type == "Pro dette": 
                clients = get_all_clients(client_type="professionnel", with_debt=True)
            elif filter_type == "Particulier": 
                clients = get_all_clients(client_type="particulier")
            elif filter_type == "Prospect":
                clients = get_all_prospects()
            else:
                clients = get_all_clients()
        
        count = 0
        for c in clients:
            email = c['email'] if 'email' in c.keys() else None
            if email:
                count += 1
                frame = ctk.CTkFrame(self.recipients_list, fg_color="#2a2a2a")
                frame.pack(fill="x", pady=1, padx=5)
                
                name = c['name'] if 'name' in c.keys() else "Sans nom"
                is_prospect = bool(c['is_prospect']) if 'is_prospect' in c.keys() else False
                icon = "🎯" if is_prospect else "👤"
                ctk.CTkLabel(frame, text=f"{icon} {name}", font=("Helvetica", 11)).pack(side="left", padx=10, pady=5)
                ctk.CTkLabel(frame, text=email, text_color="#888", font=("Helvetica", 10)).pack(side="left", padx=5)
                
                # Afficher badge prospect
                if is_prospect:
                    ctk.CTkLabel(frame, text="PROSPECT", text_color="#f39c12", 
                                 font=("Helvetica", 9, "bold")).pack(side="left", padx=5)
                
                # Afficher dette si pro
                ctype = c['client_type'] if 'client_type' in c.keys() else 'particulier'
                if ctype == 'professionnel':
                    m1 = c['dette_m1'] if 'dette_m1' in c.keys() else 0
                    m2 = c['dette_m2'] if 'dette_m2' in c.keys() else 0
                    m3 = c['dette_m3'] if 'dette_m3' in c.keys() else 0
                    m3p = c['dette_m3plus'] if 'dette_m3plus' in c.keys() else 0
                    total = (m1 or 0) + (m2 or 0) + (m3 or 0) + (m3p or 0)
                    if total > 0:
                        ctk.CTkLabel(frame, text=f"💰 {format_price(total)}", text_color="#ff6b6b",
                                     font=("Helvetica", 10)).pack(side="right", padx=10)
        
        if count == 0:
            if filter_type == "Groupe":
                ctk.CTkLabel(self.recipients_list, text="Sélectionnez un groupe ou ajoutez des membres", 
                             text_color="#666").pack(pady=30)
            else:
                ctk.CTkLabel(self.recipients_list, text="Aucun destinataire trouvé", text_color="#666").pack(pady=30)
        
        self.recipients_count.configure(text=f"{count} destinataire(s)")
        self._update_summary()
    
    def _update_summary(self):
        if not hasattr(self, 'summary_subject'): return
        subject = self.subject_entry.get() if hasattr(self, 'subject_entry') else "(non défini)"
        self.summary_subject.configure(text=f"Sujet: {subject or '(non défini)'}")
        self.summary_blocks.configure(text=f"Blocs: {len(self.designer.blocks)}")
        self.summary_recipients.configure(text=f"Destinataires: {self.recipients_count.cget('text')}")
    
    def _send_test(self):
        email = ctk.CTkInputDialog(text="Email de test:", title="Test").get_input()
        if not email: return
        self._update_settings()
        html = self.designer.generate_html()
        subject = self.subject_entry.get() or "Test KRYSTO"
        success, msg = EmailService().send_email(email, f"[TEST] {subject}", html)
        messagebox.showinfo("Résultat", f"{'✅ Envoyé!' if success else '❌ ' + msg}")
    
    def _send_campaign(self):
        subject = self.subject_entry.get()
        if not subject: messagebox.showwarning("Attention", "Définissez un sujet"); return
        if not self.designer.blocks: messagebox.showwarning("Attention", "Aucun contenu"); return
        
        f = self.recipient_filter.get()
        if f == "Newsletter": 
            clients = get_all_clients(newsletter_only=True)
        elif f == "Pro": 
            clients = get_all_clients(client_type="professionnel")
        elif f == "Pro dette": 
            clients = get_all_clients(client_type="professionnel", with_debt=True)
        elif f == "Particulier": 
            clients = get_all_clients(client_type="particulier")
        elif f == "Prospect":
            clients = get_all_prospects()
        elif f == "Groupe":
            if self.selected_group_id:
                clients = get_group_members(self.selected_group_id)
            else:
                messagebox.showwarning("Attention", "Sélectionnez un groupe"); return
        else: 
            clients = get_all_clients()
        
        recipients = []
        for c in clients:
            email = c['email'] if 'email' in c.keys() else None
            if email:
                # Récupérer le code parrainage
                code_parrainage = c['code_parrainage'] if 'code_parrainage' in c.keys() else ''
                if not code_parrainage:
                    # Générer si manquant
                    client_id = c['id'] if 'id' in c.keys() else 0
                    name = c['name'] if 'name' in c.keys() else ''
                    code_parrainage = generate_parrainage_code(name, client_id)
                
                recipients.append({
                    "name": c['name'] if 'name' in c.keys() else '',
                    "email": email,
                    "code_parrainage": code_parrainage,
                    "dette_m1": c['dette_m1'] if 'dette_m1' in c.keys() else 0,
                    "dette_m2": c['dette_m2'] if 'dette_m2' in c.keys() else 0,
                    "dette_m3": c['dette_m3'] if 'dette_m3' in c.keys() else 0,
                    "dette_m3plus": c['dette_m3plus'] if 'dette_m3plus' in c.keys() else 0,
                })
        
        if not recipients: messagebox.showwarning("Attention", "Aucun destinataire"); return
        if not messagebox.askyesno("Confirmation", f"Envoyer à {len(recipients)} destinataire(s) ?"): return
        
        self._update_settings()
        html = self.designer.generate_html()
        
        self.progress_bar.set(0)
        self.progress_log.delete("1.0", "end")
        self.send_btn.configure(state="disabled")
        
        def progress_cb(current, total, email, success):
            self.progress_bar.set(current / total)
            self.progress_label.configure(text=f"Envoi {current}/{total}")
            self.progress_log.insert("end", f"{'✅' if success else '❌'} {email}\n")
            self.progress_log.see("end")
            self.update()
        
        def send_thread():
            results = EmailService().send_bulk(recipients, subject, html, progress_cb)
            self.after(0, lambda: self._on_complete(results))
        
        threading.Thread(target=send_thread, daemon=True).start()
    
    def _on_complete(self, results):
        self.send_btn.configure(state="normal")
        self.progress_label.configure(text="Terminé!")
        msg = f"✅ Envoyés: {results['success']}\n❌ Échecs: {results['failed']}"
        if results['errors']:
            msg += "\n\nErreurs:\n" + "\n".join(f"- {e['email']}: {e['error'][:40]}" for e in results['errors'][:5])
        messagebox.showinfo("Résultats", msg)


# ============================================================================
# STATISTIQUES FRAME
# ============================================================================
class StatistiquesFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._create_ui()
    
    def _create_ui(self):
        header = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="📊 Statistiques", font=("Helvetica", 20, "bold")).pack(side="left", padx=20, pady=15)
        ctk.CTkButton(header, text="🔄 Actualiser", fg_color=KRYSTO_PRIMARY,
                      command=self._refresh).pack(side="right", padx=20, pady=10)
        
        # Tabs pour les différentes vues
        self.tabs = ctk.CTkTabview(self, fg_color=KRYSTO_DARK)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tabs.add("📈 Vue d'ensemble")
        self.tabs.add("👥 Clients")
        self.tabs.add("💰 Revenus")
        self.tabs.add("🏆 Top Clients")
        
        self._create_overview_tab(self.tabs.tab("📈 Vue d'ensemble"))
        self._create_clients_tab(self.tabs.tab("👥 Clients"))
        self._create_revenue_tab(self.tabs.tab("💰 Revenus"))
        self._create_top_clients_tab(self.tabs.tab("🏆 Top Clients"))
        
        self._refresh()
    
    def _create_overview_tab(self, parent):
        self.overview_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.overview_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _create_clients_tab(self, parent):
        self.clients_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.clients_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _create_revenue_tab(self, parent):
        self.revenue_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.revenue_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _create_top_clients_tab(self, parent):
        self.top_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.top_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _refresh(self):
        stats = get_dashboard_stats()
        funnel = get_conversion_funnel()
        monthly = get_monthly_stats(6)
        top_clients = get_top_clients(10)
        
        # Overview
        for w in self.overview_frame.winfo_children(): w.destroy()
        
        # KPIs principaux
        kpis = ctk.CTkFrame(self.overview_frame, fg_color="transparent")
        kpis.pack(fill="x", pady=10)
        
        kpi_data = [
            ("👥", "Clients", stats['total_clients'], KRYSTO_PRIMARY),
            ("🎯", "Prospects", stats['total_prospects'], "#f39c12"),
            ("📧", "Newsletter", stats['total_newsletter'], KRYSTO_SECONDARY),
            ("📦", "Produits", stats['total_products'], "#4ecdc4"),
            ("💰", "CA Total", format_price(stats['total_revenue']), "#28a745"),
            ("📊", "CA Mois", format_price(stats['revenue_month']), "#17a2b8"),
            ("🚫", "Impayés", format_price(stats['total_debt']), "#dc3545"),
            ("📋", "Tâches", stats['tasks_pending'], "#6c5ce7"),
        ]
        
        for i, (icon, label, value, color) in enumerate(kpi_data):
            card = ctk.CTkFrame(kpis, fg_color=KRYSTO_DARK, corner_radius=10)
            card.pack(side="left", fill="both", expand=True, padx=5)
            ctk.CTkLabel(card, text=icon, font=("Helvetica", 24)).pack(pady=(15, 5))
            ctk.CTkLabel(card, text=str(value), font=("Helvetica", 18, "bold"), text_color=color).pack()
            ctk.CTkLabel(card, text=label, text_color="#888", font=("Helvetica", 10)).pack(pady=(0, 15))
        
        # Funnel de conversion
        funnel_frame = ctk.CTkFrame(self.overview_frame, fg_color=KRYSTO_DARK, corner_radius=10)
        funnel_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(funnel_frame, text="🔄 Funnel de conversion", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=15, pady=10)
        
        funnel_bar = ctk.CTkFrame(funnel_frame, fg_color="transparent")
        funnel_bar.pack(fill="x", padx=15, pady=(0, 15))
        
        funnel_items = [
            ("Prospects", funnel['prospects'], "#f39c12"),
            ("Clients", funnel['clients'], KRYSTO_PRIMARY),
            ("Avec devis", funnel['with_quotes'], "#17a2b8"),
            ("Avec factures", funnel['with_invoices'], "#28a745"),
            ("Payés", funnel['with_paid'], "#20c997"),
        ]
        
        max_val = max(v for _, v, _ in funnel_items) or 1
        for label, value, color in funnel_items:
            row = ctk.CTkFrame(funnel_bar, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, width=100).pack(side="left")
            bar_width = max(int(300 * value / max_val), 5)
            ctk.CTkFrame(row, width=bar_width, height=20, fg_color=color, corner_radius=5).pack(side="left", padx=5)
            ctk.CTkLabel(row, text=str(value), text_color=color, font=("Helvetica", 11, "bold")).pack(side="left", padx=5)
        
        # Taux de conversion
        ctk.CTkLabel(funnel_frame, text=f"Taux de conversion: {stats['conversion_rate']}%", 
                     text_color=KRYSTO_SECONDARY, font=("Helvetica", 12, "bold")).pack(anchor="w", padx=15, pady=(0, 10))
        
        # Clients tab
        for w in self.clients_frame.winfo_children(): w.destroy()
        
        info_frame = ctk.CTkFrame(self.clients_frame, fg_color=KRYSTO_DARK, corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(info_frame, text=f"📈 Nouveaux clients ce mois: {stats['new_clients_month']}", 
                     font=("Helvetica", 14)).pack(anchor="w", padx=20, pady=10)
        ctk.CTkLabel(info_frame, text=f"🎯 Prospects en attente: {stats['total_prospects']}", 
                     font=("Helvetica", 14)).pack(anchor="w", padx=20, pady=5)
        ctk.CTkLabel(info_frame, text=f"⚠️ Clients avec impayés: {stats['clients_with_debt']}", 
                     font=("Helvetica", 14)).pack(anchor="w", padx=20, pady=(5, 10))
        
        # Graphique mensuel si matplotlib disponible
        if HAS_MATPLOTLIB and monthly:
            self._draw_chart(self.clients_frame, monthly, 'new_clients', "Nouveaux clients par mois")
        
        # Revenue tab
        for w in self.revenue_frame.winfo_children(): w.destroy()
        
        rev_info = ctk.CTkFrame(self.revenue_frame, fg_color=KRYSTO_DARK, corner_radius=10)
        rev_info.pack(fill="x", pady=10)
        
        ctk.CTkLabel(rev_info, text=f"💰 CA Total: {format_price(stats['total_revenue'])}", 
                     font=("Helvetica", 16, "bold"), text_color="#28a745").pack(anchor="w", padx=20, pady=10)
        ctk.CTkLabel(rev_info, text=f"📅 CA ce mois: {format_price(stats['revenue_month'])}", 
                     font=("Helvetica", 14)).pack(anchor="w", padx=20, pady=5)
        ctk.CTkLabel(rev_info, text=f"📋 Devis en attente: {stats['quotes_pending']}", 
                     font=("Helvetica", 14)).pack(anchor="w", padx=20, pady=5)
        ctk.CTkLabel(rev_info, text=f"⏳ Factures impayées: {stats['invoices_unpaid']}", 
                     font=("Helvetica", 14), text_color="#dc3545").pack(anchor="w", padx=20, pady=(5, 10))
        
        if HAS_MATPLOTLIB and monthly:
            self._draw_chart(self.revenue_frame, monthly, 'revenue', "Revenus par mois (XPF)", is_currency=True)
        
        # Top clients tab
        for w in self.top_frame.winfo_children(): w.destroy()
        
        ctk.CTkLabel(self.top_frame, text="🏆 Top 10 Clients (par CA)", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=10)
        
        for i, client in enumerate(top_clients, 1):
            revenue = client['total_revenue'] or 0
            row = ctk.CTkFrame(self.top_frame, fg_color="#2a2a2a" if i % 2 == 0 else KRYSTO_DARK)
            row.pack(fill="x", pady=2)
            
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
            ctk.CTkLabel(row, text=medal, font=("Helvetica", 14), width=40).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=client['name'], font=("Helvetica", 12)).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=f"{client['invoice_count'] or 0} factures", text_color="#888", 
                         font=("Helvetica", 10)).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=format_price(revenue), font=("Helvetica", 12, "bold"), 
                         text_color="#28a745").pack(side="right", padx=20)
    
    def _draw_chart(self, parent, data, key, title, is_currency=False):
        """Dessine un graphique avec matplotlib."""
        try:
            fig, ax = plt.subplots(figsize=(8, 3), facecolor='#343434')
            ax.set_facecolor('#343434')
            
            months = [d['month'] for d in data]
            values = [d[key] for d in data]
            
            bars = ax.bar(months, values, color=KRYSTO_PRIMARY)
            
            ax.set_title(title, color='white', fontsize=12)
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            for spine in ax.spines.values():
                spine.set_color('#666')
            
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="x", pady=10)
            
            plt.close(fig)
        except Exception as e:
            ctk.CTkLabel(parent, text=f"Graphique non disponible: {str(e)}", text_color="#888").pack(pady=10)


# ============================================================================
# DEVIS & FACTURES FRAME
# ============================================================================
class DevisFacturesFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._create_ui()
    
    def _create_ui(self):
        header = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="📄 Devis & Factures", font=("Helvetica", 20, "bold")).pack(side="left", padx=20, pady=15)
        
        self.tabs = ctk.CTkTabview(self, fg_color=KRYSTO_DARK)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tabs.add("📝 Devis")
        self.tabs.add("🧾 Factures")
        
        self._create_quotes_tab(self.tabs.tab("📝 Devis"))
        self._create_invoices_tab(self.tabs.tab("🧾 Factures"))
    
    def _create_quotes_tab(self, parent):
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(toolbar, text="➕ Nouveau devis", fg_color=KRYSTO_PRIMARY,
                      command=self._new_quote).pack(side="left", padx=5)
        
        self.quote_filter = ctk.CTkSegmentedButton(toolbar, values=["Tous", "Brouillon", "Envoyé", "Accepté", "Refusé"],
                                                    command=lambda v: self._load_quotes())
        self.quote_filter.pack(side="left", padx=10)
        self.quote_filter.set("Tous")
        
        self.quotes_list = ctk.CTkScrollableFrame(parent, fg_color="#1a1a1a")
        self.quotes_list.pack(fill="both", expand=True, padx=10, pady=5)
        
        self._load_quotes()
    
    def _create_invoices_tab(self, parent):
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(toolbar, text="➕ Nouvelle facture", fg_color=KRYSTO_PRIMARY,
                      command=self._new_invoice).pack(side="left", padx=5)
        
        self.invoice_filter = ctk.CTkSegmentedButton(toolbar, values=["Tous", "Brouillon", "Envoyée", "Payée", "En retard"],
                                                      command=lambda v: self._load_invoices())
        self.invoice_filter.pack(side="left", padx=10)
        self.invoice_filter.set("Tous")
        
        self.invoices_list = ctk.CTkScrollableFrame(parent, fg_color="#1a1a1a")
        self.invoices_list.pack(fill="both", expand=True, padx=10, pady=5)
        
        self._load_invoices()
    
    def _load_quotes(self):
        for w in self.quotes_list.winfo_children(): w.destroy()
        
        status_filter = self.quote_filter.get().lower()
        status = status_filter if status_filter != "tous" else None
        quotes = get_all_quotes(status=status)
        
        if not quotes:
            ctk.CTkLabel(self.quotes_list, text="Aucun devis", text_color="#666").pack(pady=30)
            return
        
        for q in quotes:
            self._create_quote_row(q)
    
    def _create_quote_row(self, quote):
        status_colors = {'brouillon': '#666', 'envoyé': '#17a2b8', 'accepté': '#28a745', 'refusé': '#dc3545'}
        
        frame = ctk.CTkFrame(self.quotes_list, fg_color="#2a2a2a")
        frame.pack(fill="x", pady=3, padx=5)
        
        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
        
        row1 = ctk.CTkFrame(info, fg_color="transparent")
        row1.pack(fill="x")
        
        ctk.CTkLabel(row1, text=quote['number'], font=("Helvetica", 13, "bold")).pack(side="left")
        status = quote['status'] or 'brouillon'
        ctk.CTkLabel(row1, text=status.upper(), text_color=status_colors.get(status, '#888'),
                     font=("Helvetica", 10, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(row1, text=quote['client_name'] or "Sans client", text_color="#888").pack(side="left", padx=10)
        
        date_q = quote['date_quote'][:10] if quote['date_quote'] else ""
        ctk.CTkLabel(info, text=f"Date: {date_q} | Total: {format_price(quote['total'] or 0)}", 
                     text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
        
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(side="right", padx=10)
        
        if status == 'brouillon' or status == 'envoyé':
            ctk.CTkButton(btns, text="✅", width=35, fg_color="#28a745",
                          command=lambda q=quote: self._convert_to_invoice(q['id'])).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="📄", width=35, fg_color=KRYSTO_PRIMARY,
                      command=lambda q=quote: self._view_quote_pdf(q['id'])).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="✏️", width=35, fg_color="gray",
                      command=lambda q=quote: self._edit_quote(q['id'])).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                      command=lambda q=quote: self._delete_quote(q['id'])).pack(side="left", padx=2)
    
    def _load_invoices(self):
        for w in self.invoices_list.winfo_children(): w.destroy()
        
        status_filter = self.invoice_filter.get().lower()
        status_map = {'envoyée': 'envoyée', 'payée': 'payée', 'en retard': 'en_retard'}
        status = status_map.get(status_filter) if status_filter != "tous" and status_filter != "brouillon" else (
            'brouillon' if status_filter == 'brouillon' else None)
        invoices = get_all_invoices(status=status)
        
        if not invoices:
            ctk.CTkLabel(self.invoices_list, text="Aucune facture", text_color="#666").pack(pady=30)
            return
        
        for inv in invoices:
            self._create_invoice_row(inv)
    
    def _create_invoice_row(self, invoice):
        status_colors = {'brouillon': '#666', 'envoyée': '#17a2b8', 'payée': '#28a745', 'en_retard': '#dc3545'}
        
        frame = ctk.CTkFrame(self.invoices_list, fg_color="#2a2a2a")
        frame.pack(fill="x", pady=3, padx=5)
        
        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
        
        row1 = ctk.CTkFrame(info, fg_color="transparent")
        row1.pack(fill="x")
        
        ctk.CTkLabel(row1, text=invoice['number'], font=("Helvetica", 13, "bold")).pack(side="left")
        status = invoice['status'] or 'brouillon'
        ctk.CTkLabel(row1, text=status.upper(), text_color=status_colors.get(status, '#888'),
                     font=("Helvetica", 10, "bold")).pack(side="left", padx=10)
        ctk.CTkLabel(row1, text=invoice['client_name'] or "Sans client", text_color="#888").pack(side="left", padx=10)
        
        total = format_price(invoice['total'] or 0)
        paid = format_price(invoice['amount_paid'] or 0)
        ctk.CTkLabel(info, text=f"Total: {total} | Payé: {paid}", text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
        
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(side="right", padx=10)
        
        if status != 'payée':
            ctk.CTkButton(btns, text="💰", width=35, fg_color="#28a745",
                          command=lambda i=invoice: self._mark_paid(i['id'])).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="📄", width=35, fg_color=KRYSTO_PRIMARY,
                      command=lambda i=invoice: self._view_invoice_pdf(i['id'])).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="✏️", width=35, fg_color="gray",
                      command=lambda i=invoice: self._edit_invoice(i['id'])).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                      command=lambda i=invoice: self._delete_invoice(i['id'])).pack(side="left", padx=2)
    
    def _new_quote(self):
        QuoteEditorDialog(self, on_save=self._load_quotes)
    
    def _edit_quote(self, quote_id):
        QuoteEditorDialog(self, quote_id=quote_id, on_save=self._load_quotes)
    
    def _delete_quote(self, quote_id):
        if messagebox.askyesno("Confirmation", "Supprimer ce devis ?"):
            delete_quote(quote_id)
            self._load_quotes()
    
    def _convert_to_invoice(self, quote_id):
        if messagebox.askyesno("Conversion", "Convertir ce devis en facture ?"):
            invoice_id = convert_quote_to_invoice(quote_id)
            if invoice_id:
                messagebox.showinfo("Succès", "Facture créée!")
                self._load_quotes()
                self._load_invoices()
                self.tabs.set("🧾 Factures")
    
    def _view_quote_pdf(self, quote_id):
        generate_quote_pdf(quote_id)
    
    def _new_invoice(self):
        InvoiceEditorDialog(self, on_save=self._load_invoices)
    
    def _edit_invoice(self, invoice_id):
        InvoiceEditorDialog(self, invoice_id=invoice_id, on_save=self._load_invoices)
    
    def _delete_invoice(self, invoice_id):
        if messagebox.askyesno("Confirmation", "Supprimer cette facture ?"):
            delete_invoice(invoice_id)
            self._load_invoices()
    
    def _mark_paid(self, invoice_id):
        if messagebox.askyesno("Confirmation", "Marquer cette facture comme payée ?"):
            mark_invoice_paid(invoice_id)
            self._load_invoices()
    
    def _view_invoice_pdf(self, invoice_id):
        generate_invoice_pdf(invoice_id)


# ============================================================================
# CRM FRAME - INTERACTIONS & TÂCHES
# ============================================================================
class CRMFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._create_ui()
    
    def _create_ui(self):
        header = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="🎯 CRM", font=("Helvetica", 20, "bold")).pack(side="left", padx=20, pady=15)
        
        self.tabs = ctk.CTkTabview(self, fg_color=KRYSTO_DARK)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tabs.add("📋 Tâches")
        self.tabs.add("📞 Interactions")
        self.tabs.add("⏰ Emails programmés")
        
        self._create_tasks_tab(self.tabs.tab("📋 Tâches"))
        self._create_interactions_tab(self.tabs.tab("📞 Interactions"))
        self._create_scheduled_tab(self.tabs.tab("⏰ Emails programmés"))
    
    def _create_tasks_tab(self, parent):
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(toolbar, text="➕ Nouvelle tâche", fg_color=KRYSTO_PRIMARY,
                      command=self._new_task).pack(side="left", padx=5)
        
        self.task_filter = ctk.CTkSegmentedButton(toolbar, values=["À faire", "En cours", "Toutes"],
                                                   command=lambda v: self._load_tasks())
        self.task_filter.pack(side="left", padx=10)
        self.task_filter.set("À faire")
        
        # Tâches urgentes
        self.urgent_frame = ctk.CTkFrame(parent, fg_color="#4a1a1a", corner_radius=10)
        self.urgent_frame.pack(fill="x", padx=10, pady=5)
        
        self.tasks_list = ctk.CTkScrollableFrame(parent, fg_color="#1a1a1a")
        self.tasks_list.pack(fill="both", expand=True, padx=10, pady=5)
        
        self._load_tasks()
    
    def _create_interactions_tab(self, parent):
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(toolbar, text="➕ Nouvelle interaction", fg_color=KRYSTO_PRIMARY,
                      command=self._new_interaction).pack(side="left", padx=5)
        
        self.interactions_list = ctk.CTkScrollableFrame(parent, fg_color="#1a1a1a")
        self.interactions_list.pack(fill="both", expand=True, padx=10, pady=5)
        
        self._load_interactions()
    
    def _create_scheduled_tab(self, parent):
        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(toolbar, text="➕ Programmer un email", fg_color=KRYSTO_PRIMARY,
                      command=self._new_scheduled).pack(side="left", padx=5)
        
        self.scheduled_list = ctk.CTkScrollableFrame(parent, fg_color="#1a1a1a")
        self.scheduled_list.pack(fill="both", expand=True, padx=10, pady=5)
        
        self._load_scheduled()
    
    def _load_tasks(self):
        for w in self.tasks_list.winfo_children(): w.destroy()
        for w in self.urgent_frame.winfo_children(): w.destroy()
        
        filter_val = self.task_filter.get()
        include_completed = filter_val == "Toutes"
        status = "à faire" if filter_val == "À faire" else ("en_cours" if filter_val == "En cours" else None)
        
        tasks = get_all_tasks(status=status, include_completed=include_completed)
        overdue = get_tasks_due_today()
        
        # Tâches urgentes
        if overdue:
            ctk.CTkLabel(self.urgent_frame, text=f"⚠️ {len(overdue)} tâche(s) en retard!", 
                         font=("Helvetica", 12, "bold"), text_color="#dc3545").pack(pady=10)
        else:
            self.urgent_frame.pack_forget()
        
        if not tasks:
            ctk.CTkLabel(self.tasks_list, text="Aucune tâche", text_color="#666").pack(pady=30)
            return
        
        for task in tasks:
            self._create_task_row(task)
    
    def _create_task_row(self, task):
        priority_colors = {'haute': '#dc3545', 'normale': '#17a2b8', 'basse': '#28a745'}
        
        frame = ctk.CTkFrame(self.tasks_list, fg_color="#2a2a2a")
        frame.pack(fill="x", pady=3, padx=5)
        
        # Checkbox
        done = task['status'] == 'terminée'
        check_var = ctk.BooleanVar(value=done)
        ctk.CTkCheckBox(frame, text="", variable=check_var, width=30,
                        command=lambda t=task: self._toggle_task(t['id'], check_var.get())).pack(side="left", padx=10, pady=10)
        
        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=10)
        
        row1 = ctk.CTkFrame(info, fg_color="transparent")
        row1.pack(fill="x")
        
        title_style = ("Helvetica", 12, "overstrike") if done else ("Helvetica", 12)
        ctk.CTkLabel(row1, text=task['title'], font=title_style).pack(side="left")
        
        priority = task['priority'] or 'normale'
        ctk.CTkLabel(row1, text=priority.upper(), text_color=priority_colors.get(priority, '#888'),
                     font=("Helvetica", 9, "bold")).pack(side="left", padx=10)
        
        if task['client_name']:
            ctk.CTkLabel(row1, text=f"👤 {task['client_name']}", text_color="#888", font=("Helvetica", 10)).pack(side="left", padx=5)
        
        if task['due_date']:
            due = task['due_date'][:10]
            is_overdue = task['due_date'] < datetime.now().strftime('%Y-%m-%d') and not done
            color = "#dc3545" if is_overdue else "#888"
            ctk.CTkLabel(info, text=f"📅 Échéance: {due}", text_color=color, font=("Helvetica", 10)).pack(anchor="w")
        
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(side="right", padx=10)
        
        ctk.CTkButton(btns, text="✏️", width=35, fg_color="gray",
                      command=lambda t=task: self._edit_task(t['id'])).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                      command=lambda t=task: self._delete_task_confirm(t['id'])).pack(side="left", padx=2)
    
    def _toggle_task(self, task_id, completed):
        if completed:
            complete_task(task_id)
        else:
            save_task({'status': 'à faire'}, task_id)
        self._load_tasks()
    
    def _load_interactions(self):
        for w in self.interactions_list.winfo_children(): w.destroy()
        
        interactions = get_all_interactions(limit=50)
        
        if not interactions:
            ctk.CTkLabel(self.interactions_list, text="Aucune interaction", text_color="#666").pack(pady=30)
            return
        
        for inter in interactions:
            self._create_interaction_row(inter)
    
    def _create_interaction_row(self, inter):
        frame = ctk.CTkFrame(self.interactions_list, fg_color="#2a2a2a")
        frame.pack(fill="x", pady=3, padx=5)
        
        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
        
        row1 = ctk.CTkFrame(info, fg_color="transparent")
        row1.pack(fill="x")
        
        ctk.CTkLabel(row1, text=inter['type'], font=("Helvetica", 12)).pack(side="left")
        if inter['subject']:
            ctk.CTkLabel(row1, text=f"- {inter['subject']}", text_color="#888").pack(side="left", padx=5)
        
        ctk.CTkLabel(row1, text=f"👤 {inter['client_name'] or 'N/A'}", text_color=KRYSTO_SECONDARY,
                     font=("Helvetica", 10)).pack(side="right")
        
        date_str = inter['date_interaction'][:16] if inter['date_interaction'] else ""
        ctk.CTkLabel(info, text=date_str, text_color="#666", font=("Helvetica", 9)).pack(anchor="w")
        
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(side="right", padx=10)
        
        ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                      command=lambda i=inter: self._delete_interaction_confirm(i['id'])).pack(side="left", padx=2)
    
    def _load_scheduled(self):
        for w in self.scheduled_list.winfo_children(): w.destroy()
        
        emails = get_scheduled_emails(status='programmé')
        
        if not emails:
            ctk.CTkLabel(self.scheduled_list, text="Aucun email programmé", text_color="#666").pack(pady=30)
            return
        
        for email in emails:
            self._create_scheduled_row(email)
    
    def _create_scheduled_row(self, email):
        frame = ctk.CTkFrame(self.scheduled_list, fg_color="#2a2a2a")
        frame.pack(fill="x", pady=3, padx=5)
        
        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=15, pady=10)
        
        ctk.CTkLabel(info, text=email['subject'], font=("Helvetica", 12)).pack(anchor="w")
        ctk.CTkLabel(info, text=f"📅 {email['scheduled_date'][:16]}", text_color="#888", 
                     font=("Helvetica", 10)).pack(anchor="w")
        
        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(side="right", padx=10)
        
        ctk.CTkButton(btns, text="🗑️", width=35, fg_color="#dc3545",
                      command=lambda e=email: self._delete_scheduled_confirm(e['id'])).pack(side="left", padx=2)
    
    def _new_task(self):
        TaskEditorDialog(self, on_save=self._load_tasks)
    
    def _edit_task(self, task_id):
        TaskEditorDialog(self, task_id=task_id, on_save=self._load_tasks)
    
    def _delete_task_confirm(self, task_id):
        if messagebox.askyesno("Confirmation", "Supprimer cette tâche ?"):
            delete_task(task_id)
            self._load_tasks()
    
    def _new_interaction(self):
        InteractionEditorDialog(self, on_save=self._load_interactions)
    
    def _delete_interaction_confirm(self, inter_id):
        if messagebox.askyesno("Confirmation", "Supprimer cette interaction ?"):
            delete_interaction(inter_id)
            self._load_interactions()
    
    def _new_scheduled(self):
        ScheduledEmailDialog(self, on_save=self._load_scheduled)
    
    def _delete_scheduled_confirm(self, email_id):
        if messagebox.askyesno("Confirmation", "Supprimer cet email programmé ?"):
            delete_scheduled_email(email_id)
            self._load_scheduled()


# ============================================================================
# DIALOGS POUR CRM, DEVIS, FACTURES
# ============================================================================
class TaskEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, task_id=None, on_save=None):
        super().__init__(parent)
        self.task_id = task_id
        self.on_save = on_save
        self.title("Tâche")
        self.geometry("450x400")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
        if task_id: self._load_data()
    
    def _create_ui(self):
        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text="Titre *").pack(anchor="w")
        self.title_entry = ctk.CTkEntry(main, height=35)
        self.title_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main, text="Description").pack(anchor="w")
        self.desc_entry = ctk.CTkTextbox(main, height=60)
        self.desc_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main, text="Client (optionnel)").pack(anchor="w")
        clients = get_all_clients()
        client_names = ["Aucun"] + [c['name'] for c in clients]
        self.client_combo = ctk.CTkComboBox(main, values=client_names, width=300)
        self.client_combo.pack(anchor="w", pady=(0, 10))
        self.client_combo.set("Aucun")
        self._client_map = {c['name']: c['id'] for c in clients}
        
        row = ctk.CTkFrame(main, fg_color="transparent")
        row.pack(fill="x", pady=10)
        
        ctk.CTkLabel(row, text="Échéance:").pack(side="left")
        self.due_entry = ctk.CTkEntry(row, width=120, placeholder_text="AAAA-MM-JJ")
        self.due_entry.pack(side="left", padx=10)
        
        ctk.CTkLabel(row, text="Priorité:").pack(side="left", padx=(20, 0))
        self.priority = ctk.CTkSegmentedButton(row, values=["basse", "normale", "haute"], width=180)
        self.priority.pack(side="left", padx=10)
        self.priority.set("normale")
        
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="💾 Sauvegarder", fg_color=KRYSTO_PRIMARY, command=self._save).pack(side="left", expand=True, padx=5)
    
    def _load_data(self):
        conn = get_connection()
        task = conn.execute("SELECT * FROM tasks WHERE id=?", (self.task_id,)).fetchone()
        conn.close()
        if not task: return
        
        self.title_entry.insert(0, task['title'] or '')
        self.desc_entry.insert("1.0", task['description'] or '')
        if task['due_date']: self.due_entry.insert(0, task['due_date'][:10])
        self.priority.set(task['priority'] or 'normale')
        
        if task['client_id']:
            client = get_client(task['client_id'])
            if client: self.client_combo.set(client['name'])
    
    def _save(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Attention", "Le titre est obligatoire")
            return
        
        client_name = self.client_combo.get()
        client_id = self._client_map.get(client_name) if client_name != "Aucun" else None
        
        data = {
            'title': title,
            'description': self.desc_entry.get("1.0", "end-1c").strip(),
            'client_id': client_id,
            'due_date': self.due_entry.get() or None,
            'priority': self.priority.get(),
        }
        
        save_task(data, self.task_id)
        if self.on_save: self.on_save()
        self.destroy()


class InteractionEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.on_save = on_save
        self.title("Nouvelle interaction")
        self.geometry("450x400")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text="Client *").pack(anchor="w")
        clients = get_all_clients()
        client_names = [c['name'] for c in clients]
        self.client_combo = ctk.CTkComboBox(main, values=client_names if client_names else [""], width=300)
        self.client_combo.pack(anchor="w", pady=(0, 10))
        self._client_map = {c['name']: c['id'] for c in clients}
        
        ctk.CTkLabel(main, text="Type *").pack(anchor="w")
        self.type_combo = ctk.CTkComboBox(main, values=INTERACTION_TYPES, width=200)
        self.type_combo.pack(anchor="w", pady=(0, 10))
        self.type_combo.set(INTERACTION_TYPES[0])
        
        ctk.CTkLabel(main, text="Sujet").pack(anchor="w")
        self.subject_entry = ctk.CTkEntry(main, height=35)
        self.subject_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main, text="Détails").pack(anchor="w")
        self.content_entry = ctk.CTkTextbox(main, height=80)
        self.content_entry.pack(fill="x", pady=(0, 10))
        
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="💾 Sauvegarder", fg_color=KRYSTO_PRIMARY, command=self._save).pack(side="left", expand=True, padx=5)
    
    def _save(self):
        client_name = self.client_combo.get()
        client_id = self._client_map.get(client_name)
        
        if not client_id:
            messagebox.showwarning("Attention", "Sélectionnez un client")
            return
        
        data = {
            'client_id': client_id,
            'type': self.type_combo.get(),
            'subject': self.subject_entry.get().strip(),
            'content': self.content_entry.get("1.0", "end-1c").strip(),
        }
        
        save_interaction(data)
        if self.on_save: self.on_save()
        self.destroy()


class ScheduledEmailDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.on_save = on_save
        self.title("Programmer un email")
        self.geometry("500x350")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text="Sujet *").pack(anchor="w")
        self.subject_entry = ctk.CTkEntry(main, height=35)
        self.subject_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main, text="Date et heure d'envoi *").pack(anchor="w")
        row = ctk.CTkFrame(main, fg_color="transparent")
        row.pack(fill="x", pady=(0, 10))
        
        self.date_entry = ctk.CTkEntry(row, width=120, placeholder_text="AAAA-MM-JJ")
        self.date_entry.pack(side="left")
        ctk.CTkLabel(row, text="à").pack(side="left", padx=10)
        self.time_entry = ctk.CTkEntry(row, width=80, placeholder_text="HH:MM")
        self.time_entry.pack(side="left")
        self.time_entry.insert(0, "09:00")
        
        ctk.CTkLabel(main, text="Destinataires").pack(anchor="w")
        self.filter_combo = ctk.CTkComboBox(main, values=["Newsletter", "Tous", "Prospects", "Groupe..."], width=200)
        self.filter_combo.pack(anchor="w", pady=(0, 10))
        self.filter_combo.set("Newsletter")
        
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="📅 Programmer", fg_color=KRYSTO_PRIMARY, command=self._save).pack(side="left", expand=True, padx=5)
    
    def _save(self):
        subject = self.subject_entry.get().strip()
        date = self.date_entry.get().strip()
        time = self.time_entry.get().strip()
        
        if not subject or not date:
            messagebox.showwarning("Attention", "Remplissez tous les champs obligatoires")
            return
        
        scheduled_date = f"{date}T{time}:00"
        
        data = {
            'subject': subject,
            'scheduled_date': scheduled_date,
            'recipient_filter': self.filter_combo.get(),
        }
        
        save_scheduled_email(data)
        if self.on_save: self.on_save()
        self.destroy()


class QuoteEditorDialog(ctk.CTkToplevel):
    def __init__(self, parent, quote_id=None, on_save=None):
        super().__init__(parent)
        self.quote_id = quote_id
        self.on_save = on_save
        self.lines = []
        self.title("Devis")
        self.geometry("950x700")
        self.transient(parent)
        self.grab_set()
        
        # Charger les produits et clients (convertir en dict pour .get())
        self._products = get_all_products(active_only=True)
        self._product_map = {p['name']: dict(p) for p in self._products}
        self._product_names = ["-- Sélectionner un produit --"] + [p['name'] for p in self._products]
        
        self._clients = get_all_clients()
        self._client_map = {c['name']: dict(c) for c in self._clients}
        self._client_names = [c['name'] for c in self._clients]
        
        self._selected_client_type = 'particulier'
        
        self._create_ui()
        if quote_id: self._load_data()
    
    def _create_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header - Client et TGC
        top = ctk.CTkFrame(main, fg_color="transparent")
        top.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(top, text="Client *").pack(side="left")
        self.client_combo = ctk.CTkComboBox(top, values=self._client_names if self._client_names else [""], 
                                             width=280, command=self._on_client_changed)
        self.client_combo.pack(side="left", padx=10)
        
        self.client_type_label = ctk.CTkLabel(top, text="", text_color="#888", font=("Helvetica", 10))
        self.client_type_label.pack(side="left", padx=5)
        
        ctk.CTkLabel(top, text="TGC:").pack(side="left", padx=(30, 5))
        self.tgc_combo = ctk.CTkComboBox(top, values=list(TGC_RATES.keys()), width=120,
                                          command=lambda v: self._update_totals())
        self.tgc_combo.pack(side="left")
        self.tgc_combo.set(DEFAULT_TGC_RATE)
        
        # En-tête des colonnes
        header_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK, corner_radius=5)
        header_frame.pack(fill="x", pady=(10, 2))
        
        ctk.CTkLabel(header_frame, text="Produit", width=280, font=("Helvetica", 10, "bold")).pack(side="left", padx=5, pady=8)
        ctk.CTkLabel(header_frame, text="Qté", width=60, font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Prix unit.", width=100, font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Remise %", width=70, font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Total ligne", width=100, font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        
        # Lignes
        self.lines_frame = ctk.CTkScrollableFrame(main, height=280, fg_color="#1a1a1a")
        self.lines_frame.pack(fill="x", pady=5)
        
        add_btn = ctk.CTkButton(main, text="➕ Ajouter une ligne", fg_color=KRYSTO_SECONDARY, 
                                 text_color=KRYSTO_DARK, command=self._add_line)
        add_btn.pack(anchor="w", pady=5)
        
        # Totaux
        totals = ctk.CTkFrame(main, fg_color=KRYSTO_DARK, corner_radius=10)
        totals.pack(fill="x", pady=10)
        
        totals_inner = ctk.CTkFrame(totals, fg_color="transparent")
        totals_inner.pack(side="right", padx=20, pady=10)
        
        self.subtotal_label = ctk.CTkLabel(totals_inner, text="Sous-total: 0 XPF", font=("Helvetica", 11))
        self.subtotal_label.pack(anchor="e")
        self.discount_label = ctk.CTkLabel(totals_inner, text="Remises: -0 XPF", text_color="#f39c12", font=("Helvetica", 11))
        self.discount_label.pack(anchor="e")
        self.tgc_label = ctk.CTkLabel(totals_inner, text="TGC (11%): 0 XPF", font=("Helvetica", 11))
        self.tgc_label.pack(anchor="e")
        self.total_label = ctk.CTkLabel(totals_inner, text="TOTAL: 0 XPF", font=("Helvetica", 16, "bold"), text_color=KRYSTO_SECONDARY)
        self.total_label.pack(anchor="e", pady=(5, 0))
        
        # Notes
        ctk.CTkLabel(main, text="Notes").pack(anchor="w")
        self.notes_entry = ctk.CTkTextbox(main, height=50)
        self.notes_entry.pack(fill="x", pady=(0, 10))
        
        # Buttons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", command=self.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Sauvegarder", fg_color=KRYSTO_PRIMARY, command=self._save).pack(side="right", padx=5)
        
        self._add_line()  # Ajouter une ligne par défaut
    
    def _on_client_changed(self, client_name):
        """Met à jour le type de client et les prix des lignes."""
        client = self._client_map.get(client_name)
        if client:
            client_type = client.get('client_type', 'particulier')
            self._selected_client_type = client_type
            
            type_label = "👤 Particulier" if client_type == 'particulier' else "🏢 Professionnel"
            type_color = "#17a2b8" if client_type == 'particulier' else "#28a745"
            self.client_type_label.configure(text=type_label, text_color=type_color)
            
            # Mettre à jour les prix des lignes existantes
            for line in self.lines:
                if line['frame'].winfo_exists() and line.get('product_id'):
                    # Chercher dans _product_map (qui contient des dicts)
                    product = next((p for p in self._product_map.values() if p['id'] == line['product_id']), None)
                    if product:
                        price = self._get_price_for_client_type(product)
                        line['price'].delete(0, 'end')
                        line['price'].insert(0, str(int(price)))
            
            self._update_totals()
    
    def _get_price_for_client_type(self, product):
        """Retourne le prix selon le type de client."""
        if self._selected_client_type == 'professionnel':
            return product.get('prix_pro') or product.get('price') or 0
        else:
            return product.get('prix_particulier') or product.get('price') or 0
    
    def _add_line(self, description="", quantity=1, unit_price=0, product_id=None, discount=0):
        frame = ctk.CTkFrame(self.lines_frame, fg_color="#2a2a2a")
        frame.pack(fill="x", pady=2)
        
        # Sélecteur de produit
        product_combo = ctk.CTkComboBox(frame, values=self._product_names, width=280)
        product_combo.pack(side="left", padx=5, pady=5)
        
        qty = ctk.CTkEntry(frame, placeholder_text="Qté", width=60)
        qty.pack(side="left", padx=5)
        qty.insert(0, str(quantity))
        qty.bind("<KeyRelease>", lambda e: self._update_totals())
        
        price = ctk.CTkEntry(frame, placeholder_text="Prix", width=100)
        price.pack(side="left", padx=5)
        price.insert(0, str(int(unit_price)))
        price.bind("<KeyRelease>", lambda e: self._update_totals())
        
        discount_entry = ctk.CTkEntry(frame, placeholder_text="0", width=70)
        discount_entry.pack(side="left", padx=5)
        discount_entry.insert(0, str(int(discount)))
        discount_entry.bind("<KeyRelease>", lambda e: self._update_totals())
        
        line_total = ctk.CTkLabel(frame, text="0 XPF", width=100, text_color=KRYSTO_SECONDARY)
        line_total.pack(side="left", padx=5)
        
        ctk.CTkButton(frame, text="🗑️", width=30, fg_color="#dc3545",
                      command=lambda f=frame: self._remove_line(f)).pack(side="right", padx=5)
        
        line_data = {
            'frame': frame, 
            'product_combo': product_combo,
            'qty': qty, 
            'price': price, 
            'discount': discount_entry,
            'line_total': line_total,
            'product_id': product_id
        }
        
        # Si on a un produit_id (édition), retrouver le produit dans _product_map
        if product_id:
            product = next((p for p in self._product_map.values() if p['id'] == product_id), None)
            if product:
                product_combo.set(product['name'])
        elif description:
            # Chercher si la description correspond à un produit
            product = self._product_map.get(description)
            if product:
                product_combo.set(product['name'])
                line_data['product_id'] = product['id']
        
        # Événement de changement de produit
        def on_product_selected(choice):
            if choice != "-- Sélectionner un produit --":
                product = self._product_map.get(choice)
                if product:
                    line_data['product_id'] = product['id']
                    price_value = self._get_price_for_client_type(product)
                    price.delete(0, 'end')
                    price.insert(0, str(int(price_value)))
                    self._update_totals()
        
        product_combo.configure(command=on_product_selected)
        
        self.lines.append(line_data)
        self._update_totals()
    
    def _remove_line(self, frame):
        frame.destroy()
        self.lines = [l for l in self.lines if l['frame'].winfo_exists()]
        self._update_totals()
    
    def _update_totals(self):
        subtotal_brut = 0
        total_discount = 0
        
        for line in self.lines:
            if not line['frame'].winfo_exists(): continue
            try:
                qty = float(line['qty'].get() or 0)
                price = float(line['price'].get() or 0)
                discount_percent = float(line['discount'].get() or 0)
                
                brut = qty * price
                discount_amount = brut * discount_percent / 100
                net = brut - discount_amount
                
                subtotal_brut += brut
                total_discount += discount_amount
                
                line['line_total'].configure(text=format_price(net))
            except: 
                line['line_total'].configure(text="0 XPF")
        
        subtotal_net = subtotal_brut - total_discount
        
        tgc_rate = self.tgc_combo.get()
        tgc_percent = TGC_RATES.get(tgc_rate, 11)
        tgc_amount = subtotal_net * tgc_percent / 100
        total = subtotal_net + tgc_amount
        
        self.subtotal_label.configure(text=f"Sous-total: {format_price(subtotal_brut)}")
        self.discount_label.configure(text=f"Remises: -{format_price(total_discount)}")
        self.tgc_label.configure(text=f"TGC ({tgc_percent}%): {format_price(tgc_amount)}")
        self.total_label.configure(text=f"TOTAL: {format_price(total)}")
    
    def _load_data(self):
        quote, lines = get_quote(self.quote_id)
        if not quote: return
        
        if quote['client_name']:
            self.client_combo.set(quote['client_name'])
            self._on_client_changed(quote['client_name'])
        self.tgc_combo.set(quote['tgc_rate'] or DEFAULT_TGC_RATE)
        self.notes_entry.insert("1.0", quote['notes'] or '')
        
        # Clear default line and add actual lines
        for l in self.lines:
            l['frame'].destroy()
        self.lines = []
        
        for line in lines:
            self._add_line(
                description=line['description'], 
                quantity=line['quantity'], 
                unit_price=line['unit_price'], 
                product_id=line['product_id'],
                discount=line.get('discount_percent', 0)
            )
    
    def _save(self):
        client_name = self.client_combo.get()
        client = self._client_map.get(client_name)
        
        if not client:
            messagebox.showwarning("Attention", "Sélectionnez un client")
            return
        
        lines_data = []
        for line in self.lines:
            if not line['frame'].winfo_exists(): continue
            
            product_name = line['product_combo'].get()
            if product_name == "-- Sélectionner un produit --":
                continue
            
            product = self._product_map.get(product_name)
            if not product:
                continue
            
            try:
                qty = float(line['qty'].get() or 1)
                price = float(line['price'].get() or 0)
                discount = float(line['discount'].get() or 0)
            except:
                qty, price, discount = 1, 0, 0
            
            total = qty * price * (1 - discount / 100)
            
            lines_data.append({
                'description': product['name'],
                'quantity': qty,
                'unit_price': price,
                'discount_percent': discount,
                'total': total,
                'product_id': product['id'],
            })
        
        if not lines_data:
            messagebox.showwarning("Attention", "Ajoutez au moins une ligne avec un produit")
            return
        
        data = {
            'client_id': client['id'],
            'tgc_rate': self.tgc_combo.get(),
            'notes': self.notes_entry.get("1.0", "end-1c").strip(),
            'status': 'brouillon',
        }
        
        save_quote(data, lines_data, self.quote_id)
        if self.on_save: self.on_save()
        self.destroy()


class InvoiceEditorDialog(QuoteEditorDialog):
    """Réutilise QuoteEditorDialog avec quelques modifications."""
    def __init__(self, parent, invoice_id=None, on_save=None):
        self.invoice_id = invoice_id
        super().__init__(parent, quote_id=None, on_save=on_save)
        self.title("Facture")
    
    def _load_data(self):
        if not self.invoice_id: return
        invoice, lines = get_invoice(self.invoice_id)
        if not invoice: return
        
        if invoice['client_name']:
            self.client_combo.set(invoice['client_name'])
            self._on_client_changed(invoice['client_name'])
        self.tgc_combo.set(invoice['tgc_rate'] or DEFAULT_TGC_RATE)
        self.notes_entry.insert("1.0", invoice['notes'] or '')
        
        for l in self.lines:
            l['frame'].destroy()
        self.lines = []
        
        for line in lines:
            self._add_line(
                description=line['description'],
                quantity=line['quantity'], 
                unit_price=line['unit_price'], 
                product_id=line['product_id'],
                discount=line.get('discount_percent', 0)
            )
    
    def _save(self):
        client_name = self.client_combo.get()
        client = self._client_map.get(client_name)
        
        if not client:
            messagebox.showwarning("Attention", "Sélectionnez un client")
            return
        
        lines_data = []
        for line in self.lines:
            if not line['frame'].winfo_exists(): continue
            
            product_name = line['product_combo'].get()
            if product_name == "-- Sélectionner un produit --":
                continue
            
            product = self._product_map.get(product_name)
            if not product:
                continue
            
            try:
                qty = float(line['qty'].get() or 1)
                price = float(line['price'].get() or 0)
                discount = float(line['discount'].get() or 0)
            except:
                qty, price, discount = 1, 0, 0
            
            total = qty * price * (1 - discount / 100)
            
            lines_data.append({
                'description': product['name'],
                'quantity': qty,
                'unit_price': price,
                'discount_percent': discount,
                'total': total,
                'product_id': product['id'],
            })
        
        if not lines_data:
            messagebox.showwarning("Attention", "Ajoutez au moins une ligne avec un produit")
            return
        
        data = {
            'client_id': client['id'],
            'tgc_rate': self.tgc_combo.get(),
            'notes': self.notes_entry.get("1.0", "end-1c").strip(),
            'status': 'brouillon',
        }
        
        save_invoice(data, lines_data, self.invoice_id)
        if self.on_save: self.on_save()
        self.destroy()


# ============================================================================
# GÉNÉRATION PDF
# ============================================================================
def generate_quote_pdf(quote_id):
    """Génère le PDF d'un devis."""
    quote, lines = get_quote(quote_id)
    if not quote: return
    
    if HAS_REPORTLAB:
        _generate_document_pdf_reportlab(quote, lines, "Devis", quote['number'])
    else:
        _generate_document_html(quote, lines, "Devis", quote['number'])


def generate_invoice_pdf(invoice_id):
    """Génère le PDF d'une facture."""
    invoice, lines = get_invoice(invoice_id)
    if not invoice: return
    
    if HAS_REPORTLAB:
        _generate_document_pdf_reportlab(invoice, lines, "Facture", invoice['number'])
    else:
        _generate_document_html(invoice, lines, "Facture", invoice['number'])


def _generate_document_html(doc, lines, doc_type, number):
    """Génère un document HTML à la place du PDF."""
    tgc_percent = TGC_RATES.get(doc['tgc_rate'], 11)
    
    lines_html = ""
    for line in lines:
        lines_html += f"""<tr>
            <td style="padding:10px;border-bottom:1px solid #ddd;">{line['description']}</td>
            <td style="padding:10px;border-bottom:1px solid #ddd;text-align:center;">{line['quantity']}</td>
            <td style="padding:10px;border-bottom:1px solid #ddd;text-align:right;">{format_price(line['unit_price'])}</td>
            <td style="padding:10px;border-bottom:1px solid #ddd;text-align:right;">{format_price(line['total'])}</td>
        </tr>"""
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{doc_type} {number}</title>
<style>body{{font-family:Arial,sans-serif;margin:40px;}}
.header{{display:flex;justify-content:space-between;margin-bottom:40px;}}
.company{{font-size:24px;font-weight:bold;color:{KRYSTO_PRIMARY};}}
table{{width:100%;border-collapse:collapse;margin:20px 0;}}
th{{background:{KRYSTO_PRIMARY};color:white;padding:12px;text-align:left;}}
.totals{{text-align:right;margin-top:20px;}}
.total{{font-size:20px;font-weight:bold;color:{KRYSTO_PRIMARY};}}</style></head>
<body>
<div class="header">
    <div>
        <div class="company">{COMPANY_NAME}</div>
        <div>{COMPANY_ADDRESS}</div>
        <div>{COMPANY_EMAIL} | {COMPANY_PHONE}</div>
        {f'<div>RIDET: {COMPANY_RIDET}</div>' if COMPANY_RIDET else ''}
    </div>
    <div style="text-align:right;">
        <h1>{doc_type} {number}</h1>
        <div>Date: {doc.get('date_quote', doc.get('date_invoice', ''))[:10]}</div>
    </div>
</div>
<div style="margin-bottom:30px;">
    <strong>Client:</strong><br>
    {doc['client_name']}<br>
    {doc.get('client_address', '') or ''}<br>
    {doc.get('client_email', '') or ''}
</div>
<table>
    <thead><tr><th>Description</th><th style="width:80px;">Qté</th><th style="width:120px;">Prix unit.</th><th style="width:120px;">Total</th></tr></thead>
    <tbody>{lines_html}</tbody>
</table>
<div class="totals">
    <div>Sous-total: {format_price(doc['subtotal'])}</div>
    <div>TGC ({tgc_percent}%): {format_price(doc['tgc_amount'])}</div>
    <div class="total">TOTAL: {format_price(doc['total'])}</div>
</div>
{f'<div style="margin-top:30px;"><strong>Notes:</strong><br>{doc["notes"]}</div>' if doc.get('notes') else ''}
</body></html>"""
    
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html)
        webbrowser.open('file://' + f.name)


def _generate_document_pdf_reportlab(doc, lines, doc_type, number):
    """Génère un vrai PDF avec ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    
    filepath = tempfile.mktemp(suffix='.pdf')
    doc_pdf = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor(KRYSTO_PRIMARY))
    
    story = []
    
    # Header
    story.append(Paragraph(f"{COMPANY_NAME}", title_style))
    story.append(Paragraph(f"{COMPANY_ADDRESS}<br/>{COMPANY_EMAIL} | {COMPANY_PHONE}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Document info
    story.append(Paragraph(f"<b>{doc_type} {number}</b>", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    # Client
    story.append(Paragraph(f"<b>Client:</b> {doc['client_name']}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Table
    data = [['Description', 'Qté', 'Prix unit.', 'Total']]
    for line in lines:
        data.append([line['description'], str(line['quantity']), format_price(line['unit_price']), format_price(line['total'])])
    
    table = Table(data, colWidths=[10*cm, 2*cm, 3*cm, 3*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(KRYSTO_PRIMARY)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))
    
    # Totals
    tgc_percent = TGC_RATES.get(doc['tgc_rate'], 11)
    story.append(Paragraph(f"Sous-total: {format_price(doc['subtotal'])}", styles['Normal']))
    story.append(Paragraph(f"TGC ({tgc_percent}%): {format_price(doc['tgc_amount'])}", styles['Normal']))
    story.append(Paragraph(f"<b>TOTAL: {format_price(doc['total'])}</b>", styles['Heading3']))
    
    doc_pdf.build(story)
    webbrowser.open('file://' + filepath)


# ============================================================================
# CAISSE - POINT DE VENTE
# ============================================================================
class CaisseFrame(ctk.CTkFrame):
    """Interface de caisse / Point de vente avec onglets."""
    
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.panier = []
        self.current_client = None
        self._create_ui()
        self._reset_sale()
    
    def _create_ui(self):
        # Header principal
        header = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        
        # Ligne 1: Titre et boutons
        row1 = ctk.CTkFrame(header, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(row1, text="🛒 Caisse", font=("Helvetica", 22, "bold")).pack(side="left")
        
        # Date/heure
        self.datetime_label = ctk.CTkLabel(row1, text="", text_color="#888")
        self.datetime_label.pack(side="left", padx=30)
        self._update_datetime()
        
        # Boutons
        ctk.CTkButton(row1, text="🧾 Clôture Z", fg_color="#6c5ce7", width=110,
                      command=self._generate_ticket_z).pack(side="right", padx=5)
        ctk.CTkButton(row1, text="🔄 Nouvelle vente", fg_color="#dc3545", width=130,
                      command=self._reset_sale).pack(side="right", padx=5)
        
        # Ligne 2: Objectif CA et progression
        row2 = ctk.CTkFrame(header, fg_color="#2a2a2a", corner_radius=8)
        row2.pack(fill="x", padx=15, pady=(5, 10))
        
        # Objectif CA
        obj_frame = ctk.CTkFrame(row2, fg_color="transparent")
        obj_frame.pack(side="left", padx=15, pady=10)
        
        ctk.CTkLabel(obj_frame, text="🎯 Objectif:", font=("Helvetica", 11)).pack(side="left")
        
        self.objectif_entry = ctk.CTkEntry(obj_frame, width=100, height=30, placeholder_text="0")
        self.objectif_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(obj_frame, text="✓", width=30, height=30, fg_color=KRYSTO_PRIMARY,
                      command=self._save_objectif).pack(side="left", padx=2)
        
        # Affichage progression
        progress_frame = ctk.CTkFrame(row2, fg_color="transparent")
        progress_frame.pack(side="left", fill="x", expand=True, padx=20, pady=10)
        
        self.ca_label = ctk.CTkLabel(progress_frame, text="CA: 0 XPF / 0 XPF", font=("Helvetica", 12, "bold"))
        self.ca_label.pack(anchor="w")
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame, width=400, height=20)
        self.progress_bar.pack(fill="x", pady=(5, 0))
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(progress_frame, text="0%", font=("Helvetica", 10), text_color=KRYSTO_SECONDARY)
        self.progress_label.pack(anchor="e")
        
        # Stats ventes du jour
        stats_frame = ctk.CTkFrame(row2, fg_color="transparent")
        stats_frame.pack(side="right", padx=15, pady=10)
        
        self.stats_label = ctk.CTkLabel(stats_frame, text="", font=("Helvetica", 10))
        self.stats_label.pack()
        
        # Onglets
        self.tabview = ctk.CTkTabview(self, fg_color=KRYSTO_DARK)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.tab_vente = self.tabview.add("🛒 Vente")
        self.tab_historique = self.tabview.add("📋 Historique")
        self.tab_tickets_z = self.tabview.add("🧾 Tickets Z")
        
        self._create_vente_tab()
        self._create_historique_tab()
        self._create_tickets_z_tab()
        
        # Charger l'objectif du jour
        self._load_objectif()
        self._update_stats()
    
    def _load_objectif(self):
        """Charge l'objectif CA du jour."""
        objectif = get_objectif_ca()
        self.objectif_entry.delete(0, 'end')
        if objectif > 0:
            self.objectif_entry.insert(0, str(int(objectif)))
    
    def _save_objectif(self):
        """Sauvegarde l'objectif CA du jour."""
        try:
            objectif = float(self.objectif_entry.get() or 0)
            set_objectif_ca(objectif)
            self._update_stats()
            messagebox.showinfo("Objectif", f"Objectif CA défini: {format_price(objectif)}")
        except ValueError:
            messagebox.showwarning("Erreur", "Veuillez entrer un nombre valide")
    
    def _create_vente_tab(self):
        """Crée l'onglet de vente."""
        main = ctk.CTkFrame(self.tab_vente, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Colonne gauche - Produits et recherche
        left_col = ctk.CTkFrame(main, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Section Client
        client_frame = ctk.CTkFrame(left_col, fg_color="#2a2a2a", corner_radius=10)
        client_frame.pack(fill="x", pady=(0, 10))
        
        client_header = ctk.CTkFrame(client_frame, fg_color="transparent")
        client_header.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(client_header, text="👤 Client", font=("Helvetica", 13, "bold")).pack(side="left")
        ctk.CTkButton(client_header, text="➕ Nouveau", fg_color=KRYSTO_SECONDARY, 
                      text_color=KRYSTO_DARK, width=100, height=28,
                      command=self._create_new_client).pack(side="right")
        
        client_select = ctk.CTkFrame(client_frame, fg_color="transparent")
        client_select.pack(fill="x", padx=15, pady=(0, 10))
        
        self._load_clients_list()
        self.client_combo = ctk.CTkComboBox(client_select, values=self._client_names, width=300,
                                             command=self._on_client_selected)
        self.client_combo.pack(side="left")
        
        self.client_info_label = ctk.CTkLabel(client_select, text="", text_color="#888", font=("Helvetica", 10))
        self.client_info_label.pack(side="left", padx=15)
        
        # Section Recherche produits
        search_frame = ctk.CTkFrame(left_col, fg_color="#2a2a2a", corner_radius=10)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(search_frame, text="🔍 Ajouter un produit", font=("Helvetica", 13, "bold")).pack(anchor="w", padx=15, pady=10)
        
        search_row = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.search_entry = ctk.CTkEntry(search_row, placeholder_text="Rechercher...", width=280, height=38)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", self._on_search)
        self.search_entry.bind("<Return>", self._add_first_result)
        
        # Liste des produits filtrés
        self.products_list = ctk.CTkScrollableFrame(left_col, fg_color="#2a2a2a", height=300)
        self.products_list.pack(fill="both", expand=True)
        
        self._load_products()
        
        # Colonne droite - Panier et total
        right_col = ctk.CTkFrame(main, fg_color="#2a2a2a", corner_radius=10, width=380)
        right_col.pack(side="right", fill="both", padx=(5, 0))
        right_col.pack_propagate(False)
        
        # Header panier
        panier_header = ctk.CTkFrame(right_col, fg_color="transparent")
        panier_header.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(panier_header, text="🧾 Panier", font=("Helvetica", 14, "bold")).pack(side="left")
        self.panier_count = ctk.CTkLabel(panier_header, text="0 article(s)", text_color="#888")
        self.panier_count.pack(side="right")
        
        # Liste panier
        self.panier_frame = ctk.CTkScrollableFrame(right_col, fg_color="#1a1a1a", height=250)
        self.panier_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Totaux
        totals_frame = ctk.CTkFrame(right_col, fg_color="#1a1a1a", corner_radius=10)
        totals_frame.pack(fill="x", padx=10, pady=10)
        
        self.subtotal_label = ctk.CTkLabel(totals_frame, text="Sous-total: 0 XPF", font=("Helvetica", 12))
        self.subtotal_label.pack(anchor="e", padx=15, pady=(10, 2))
        
        self.tgc_label = ctk.CTkLabel(totals_frame, text="TGC (11%): 0 XPF", font=("Helvetica", 12))
        self.tgc_label.pack(anchor="e", padx=15, pady=2)
        
        self.total_label = ctk.CTkLabel(totals_frame, text="TOTAL: 0 XPF", 
                                         font=("Helvetica", 20, "bold"), text_color=KRYSTO_SECONDARY)
        self.total_label.pack(anchor="e", padx=15, pady=(5, 10))
        
        # Boutons de paiement
        payment_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        payment_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(payment_frame, text="💵 Espèces", fg_color="#28a745", height=45, width=110,
                      font=("Helvetica", 12, "bold"), command=lambda: self._finalize_sale("espèces")).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(payment_frame, text="💳 Carte", fg_color="#17a2b8", height=45, width=110,
                      font=("Helvetica", 12, "bold"), command=lambda: self._finalize_sale("carte")).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(payment_frame, text="📱 Autre", fg_color="#6c5ce7", height=45, width=110,
                      font=("Helvetica", 12, "bold"), command=lambda: self._finalize_sale("autre")).pack(side="left", expand=True, padx=2)
    
    def _create_historique_tab(self):
        """Crée l'onglet historique des ventes."""
        # Filtres
        filter_frame = ctk.CTkFrame(self.tab_historique, fg_color="#2a2a2a", corner_radius=10)
        filter_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(filter_frame, text="📅 Période:", font=("Helvetica", 12)).pack(side="left", padx=15, pady=10)
        
        self.date_filter = ctk.CTkComboBox(filter_frame, values=["Aujourd'hui", "Cette semaine", "Ce mois", "Tout"], width=150)
        self.date_filter.pack(side="left", padx=5)
        self.date_filter.set("Aujourd'hui")
        
        ctk.CTkButton(filter_frame, text="🔄 Actualiser", fg_color=KRYSTO_PRIMARY, width=100,
                      command=self._load_historique).pack(side="left", padx=10)
        
        # Totaux période
        self.period_stats = ctk.CTkLabel(filter_frame, text="", font=("Helvetica", 11), text_color=KRYSTO_SECONDARY)
        self.period_stats.pack(side="right", padx=15)
        
        # Liste des ventes
        self.historique_list = ctk.CTkScrollableFrame(self.tab_historique, fg_color="#2a2a2a")
        self.historique_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self._load_historique()
    
    def _create_tickets_z_tab(self):
        """Crée l'onglet des tickets Z."""
        # Header
        header = ctk.CTkFrame(self.tab_tickets_z, fg_color="#2a2a2a", corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text="🧾 Tickets Z - Clôtures de caisse", font=("Helvetica", 14, "bold")).pack(side="left", padx=15, pady=15)
        
        ctk.CTkButton(header, text="🔄 Actualiser", fg_color=KRYSTO_PRIMARY, width=100,
                      command=self._load_tickets_z).pack(side="right", padx=15, pady=10)
        
        # Liste des tickets Z
        self.tickets_z_list = ctk.CTkScrollableFrame(self.tab_tickets_z, fg_color="#2a2a2a")
        self.tickets_z_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self._load_tickets_z()
    
    def _update_stats(self):
        """Met à jour les statistiques du jour avec progression objectif."""
        stats = get_caisse_stats_today()
        
        # Texte stats
        text = f"📊 {stats['nb_sales']} vente(s) | 💵 {format_price(stats['total_especes'])} | 💳 {format_price(stats['total_carte'])}"
        self.stats_label.configure(text=text)
        
        # Mise à jour CA et progression
        objectif = stats['objectif_ca'] or 0
        total = stats['total_ttc'] or 0
        progression = stats['progression'] or 0
        
        self.ca_label.configure(text=f"CA: {format_price(total)} / {format_price(objectif)}")
        self.progress_bar.set(progression / 100)
        
        # Couleur selon progression
        if progression >= 100:
            color = "#28a745"  # Vert
            emoji = "🎉"
        elif progression >= 75:
            color = KRYSTO_SECONDARY  # Jaune
            emoji = "🔥"
        elif progression >= 50:
            color = "#17a2b8"  # Bleu
            emoji = "📈"
        else:
            color = "#888"
            emoji = "🎯"
        
        self.progress_label.configure(text=f"{emoji} {progression:.0f}%", text_color=color)
    
    def _update_datetime(self):
        """Met à jour l'affichage de la date/heure."""
        self.datetime_label.configure(text=datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.after(60000, self._update_datetime)  # Mise à jour chaque minute
    
    def _load_clients_list(self):
        """Charge la liste des clients pour le combobox."""
        clients = get_all_clients()
        client_comptoir = get_client_comptoir()
        
        self._clients = [dict(c) for c in clients]
        self._client_map = {c['name']: c for c in self._clients}
        
        # Mettre Client Comptoir en premier
        self._client_names = []
        if client_comptoir:
            comptoir_name = "🏪 Client Comptoir (vente anonyme)"
            self._client_names.append(comptoir_name)
            self._client_map[comptoir_name] = dict(client_comptoir)
        
        # Ajouter les autres clients
        for c in self._clients:
            if c.get('code_parrainage') != CLIENT_COMPTOIR_CODE:
                display_name = f"{c['name']}" + (f" ({c['email']})" if c.get('email') else "")
                self._client_names.append(display_name)
                self._client_map[display_name] = c
    
    def _on_client_selected(self, choice):
        """Appelé quand un client est sélectionné."""
        client = self._client_map.get(choice)
        if client:
            self.current_client = client
            
            # Afficher les infos du client
            info_parts = []
            if client.get('email'):
                info_parts.append(f"📧 {client['email']}")
            if client.get('phone'):
                info_parts.append(f"📞 {client['phone']}")
            if client.get('client_type') == 'professionnel':
                info_parts.append("🏢 Pro")
            
            self.client_info_label.configure(text=" | ".join(info_parts) if info_parts else "Client anonyme")
    
    def _create_new_client(self):
        """Ouvre le dialogue de création de client rapide."""
        CaisseClientDialog(self, on_save=self._on_new_client_created)
    
    def _on_new_client_created(self, client_id):
        """Appelé après création d'un nouveau client."""
        self._load_clients_list()
        
        # Rafraîchir le combobox
        self.client_combo.configure(values=self._client_names)
        
        # Sélectionner le nouveau client
        client = get_client(client_id)
        if client:
            client_dict = dict(client)
            display_name = f"{client_dict['name']}" + (f" ({client_dict['email']})" if client_dict.get('email') else "")
            self.client_combo.set(display_name)
            self._on_client_selected(display_name)
    
    def _load_products(self, search_term=""):
        """Charge et affiche les produits."""
        for w in self.products_list.winfo_children():
            w.destroy()
        
        products = get_all_products(active_only=True)
        
        # Filtrer si recherche
        if search_term:
            search_lower = search_term.lower()
            products = [p for p in products if search_lower in p['name'].lower() or 
                        (p['category'] and search_lower in p['category'].lower())]
        
        if not products:
            ctk.CTkLabel(self.products_list, text="Aucun produit trouvé", text_color="#666").pack(pady=20)
            return
        
        self._filtered_products = products
        
        for p in products[:20]:  # Limiter à 20 pour la performance
            self._create_product_button(p)
    
    def _create_product_button(self, product):
        """Crée un bouton produit cliquable."""
        # Convertir en dict si nécessaire
        p = dict(product) if not isinstance(product, dict) else product
        
        frame = ctk.CTkFrame(self.products_list, fg_color="#2a2a2a", cursor="hand2")
        frame.pack(fill="x", pady=2, padx=5)
        frame.bind("<Button-1>", lambda e, prod=p: self._add_to_panier(prod))
        
        # Rendre les enfants cliquables aussi
        info = ctk.CTkFrame(frame, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        info.bind("<Button-1>", lambda e, prod=p: self._add_to_panier(prod))
        
        name_label = ctk.CTkLabel(info, text=p['name'], font=("Helvetica", 12))
        name_label.pack(anchor="w")
        name_label.bind("<Button-1>", lambda e, prod=p: self._add_to_panier(prod))
        
        # Prix selon type client
        if self.current_client and self.current_client.get('client_type') == 'professionnel':
            price = p.get('prix_pro') or p.get('price') or 0
            price_text = f"🏢 {format_price(price)}"
        else:
            price = p.get('prix_particulier') or p.get('price') or 0
            price_text = f"👤 {format_price(price)}"
        
        price_label = ctk.CTkLabel(frame, text=price_text, text_color=KRYSTO_SECONDARY, 
                                    font=("Helvetica", 11, "bold"))
        price_label.pack(side="right", padx=15)
        price_label.bind("<Button-1>", lambda e, prod=p: self._add_to_panier(prod))
        
        stock = p.get('stock') or 0
        stock_label = ctk.CTkLabel(frame, text=f"📦 {stock}", text_color="#888", font=("Helvetica", 10))
        stock_label.pack(side="right", padx=5)
        stock_label.bind("<Button-1>", lambda e, prod=p: self._add_to_panier(prod))
    
    def _on_search(self, event=None):
        """Recherche de produits."""
        search_term = self.search_entry.get().strip()
        self._load_products(search_term)
    
    def _add_first_result(self, event=None):
        """Ajoute le premier résultat de recherche au panier."""
        if hasattr(self, '_filtered_products') and self._filtered_products:
            self._add_to_panier(self._filtered_products[0])
            self.search_entry.delete(0, 'end')
            self._load_products()
    
    def _add_to_panier(self, product):
        """Ajoute un produit au panier."""
        product_dict = dict(product) if not isinstance(product, dict) else product
        
        # Vérifier si déjà dans le panier
        for item in self.panier:
            if item['product_id'] == product_dict['id']:
                item['quantity'] += 1
                self._update_panier_display()
                return
        
        # Prix selon type client
        if self.current_client and self.current_client.get('client_type') == 'professionnel':
            price = product_dict.get('prix_pro') or product_dict.get('price') or 0
        else:
            price = product_dict.get('prix_particulier') or product_dict.get('price') or 0
        
        # Ajouter au panier
        self.panier.append({
            'product_id': product_dict['id'],
            'name': product_dict['name'],
            'price': price,
            'quantity': 1
        })
        
        self._update_panier_display()
    
    def _update_panier_display(self):
        """Met à jour l'affichage du panier."""
        for w in self.panier_frame.winfo_children():
            w.destroy()
        
        if not self.panier:
            ctk.CTkLabel(self.panier_frame, text="Panier vide", text_color="#666").pack(pady=30)
            self.panier_count.configure(text="0 article(s)")
            self._update_totals()
            return
        
        total_items = sum(item['quantity'] for item in self.panier)
        self.panier_count.configure(text=f"{total_items} article(s)")
        
        for i, item in enumerate(self.panier):
            frame = ctk.CTkFrame(self.panier_frame, fg_color="#2a2a2a")
            frame.pack(fill="x", pady=2)
            
            # Nom du produit
            ctk.CTkLabel(frame, text=item['name'][:25], font=("Helvetica", 11)).pack(side="left", padx=10, pady=8)
            
            # Contrôles quantité
            qty_frame = ctk.CTkFrame(frame, fg_color="transparent")
            qty_frame.pack(side="left", padx=5)
            
            ctk.CTkButton(qty_frame, text="-", width=25, height=25, fg_color="#dc3545",
                          command=lambda idx=i: self._change_quantity(idx, -1)).pack(side="left")
            
            qty_label = ctk.CTkLabel(qty_frame, text=str(item['quantity']), width=30)
            qty_label.pack(side="left", padx=5)
            
            ctk.CTkButton(qty_frame, text="+", width=25, height=25, fg_color="#28a745",
                          command=lambda idx=i: self._change_quantity(idx, 1)).pack(side="left")
            
            # Prix total ligne
            line_total = item['price'] * item['quantity']
            ctk.CTkLabel(frame, text=format_price(line_total), text_color=KRYSTO_SECONDARY,
                         font=("Helvetica", 11, "bold")).pack(side="right", padx=10)
            
            # Bouton supprimer
            ctk.CTkButton(frame, text="🗑️", width=30, height=25, fg_color="#dc3545",
                          command=lambda idx=i: self._remove_from_panier(idx)).pack(side="right", padx=2)
        
        self._update_totals()
    
    def _change_quantity(self, index, delta):
        """Change la quantité d'un article."""
        if 0 <= index < len(self.panier):
            self.panier[index]['quantity'] += delta
            if self.panier[index]['quantity'] <= 0:
                self.panier.pop(index)
            self._update_panier_display()
    
    def _remove_from_panier(self, index):
        """Supprime un article du panier."""
        if 0 <= index < len(self.panier):
            self.panier.pop(index)
            self._update_panier_display()
    
    def _update_totals(self):
        """Met à jour les totaux."""
        subtotal = sum(item['price'] * item['quantity'] for item in self.panier)
        tgc_percent = TGC_RATES.get(DEFAULT_TGC_RATE, 11)
        tgc_amount = subtotal * tgc_percent / 100
        total = subtotal + tgc_amount
        
        self.subtotal_label.configure(text=f"Sous-total: {format_price(subtotal)}")
        self.tgc_label.configure(text=f"TGC ({tgc_percent}%): {format_price(tgc_amount)}")
        self.total_label.configure(text=f"TOTAL: {format_price(total)}")
    
    def _reset_sale(self):
        """Réinitialise la vente."""
        self.panier = []
        self._load_clients_list()
        
        # Mettre Client Comptoir par défaut
        if self._client_names:
            self.client_combo.configure(values=self._client_names)
            self.client_combo.set(self._client_names[0])
            self._on_client_selected(self._client_names[0])
        
        self._update_panier_display()
        self.search_entry.delete(0, 'end')
        self._load_products()
    
    def _finalize_sale(self, payment_method):
        """Finalise la vente."""
        if not self.panier:
            messagebox.showwarning("Attention", "Le panier est vide!")
            return
        
        if not self.current_client:
            messagebox.showwarning("Attention", "Sélectionnez un client!")
            return
        
        # Calculer les totaux
        subtotal = sum(item['price'] * item['quantity'] for item in self.panier)
        tgc_percent = TGC_RATES.get(DEFAULT_TGC_RATE, 11)
        tgc_amount = subtotal * tgc_percent / 100
        total = subtotal + tgc_amount
        
        # Créer les lignes de facture
        lines = []
        for item in self.panier:
            lines.append({
                'product_id': item['product_id'],
                'description': item['name'],
                'quantity': item['quantity'],
                'unit_price': item['price'],
                'discount_percent': 0,
                'total': item['price'] * item['quantity']
            })
        
        # Créer la facture
        invoice_data = {
            'client_id': self.current_client['id'],
            'tgc_rate': DEFAULT_TGC_RATE,
            'status': 'payée',
            'amount_paid': total,
            'date_paid': datetime.now().strftime('%Y-%m-%d'),
            'notes': f"Vente au comptoir - Paiement: {payment_method}"
        }
        
        invoice_id = save_invoice(invoice_data, lines)
        
        # Enregistrer dans caisse_sales pour le ticket Z
        sale_data = {
            'client_id': self.current_client['id'],
            'subtotal': subtotal,
            'tgc_amount': tgc_amount,
            'total': total,
            'payment_method': payment_method,
            'notes': f"Facture liée"
        }
        save_caisse_sale(sale_data, invoice_id)
        
        # Récupérer le numéro de facture
        invoice, _ = get_invoice(invoice_id)
        invoice_number = invoice['number'] if invoice else f"#{invoice_id}"
        
        # Demander si envoyer par email (si le client a un email)
        is_comptoir = self.current_client.get('code_parrainage') == CLIENT_COMPTOIR_CODE
        has_email = self.current_client.get('email')
        
        if has_email and not is_comptoir:
            send_email = messagebox.askyesno("Email", 
                f"Envoyer la facture par email à {self.current_client['email']} ?")
            if send_email:
                self._send_receipt_email(invoice_id)
        
        # Message de confirmation
        messagebox.showinfo("Vente terminée", 
            f"✅ Facture {invoice_number} créée!\n\n"
            f"Total: {format_price(total)}\n"
            f"Paiement: {payment_method.upper()}\n"
            f"Client: {self.current_client['name']}")
        
        # Mettre à jour stats et historique
        self._update_stats()
        self._load_historique()
        
        # Réinitialiser pour une nouvelle vente
        self._reset_sale()
    
    def _send_receipt_email(self, invoice_id):
        """Envoie le reçu par email."""
        invoice, lines = get_invoice(invoice_id)
        if not invoice or not invoice['client_email']:
            return
        
        # Construire le contenu de l'email
        lines_html = ""
        for line in lines:
            lines_html += f"<tr><td style='padding:8px;border-bottom:1px solid #eee;'>{line['description']}</td>"
            lines_html += f"<td style='padding:8px;text-align:center;'>{line['quantity']}</td>"
            lines_html += f"<td style='padding:8px;text-align:right;'>{format_price(line['total'])}</td></tr>"
        
        tgc_percent = TGC_RATES.get(invoice['tgc_rate'], 11)
        
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <div style="text-align:center;margin-bottom:30px;">
                <h1 style="color:{KRYSTO_PRIMARY};margin:0;">{COMPANY_NAME}</h1>
                <p style="color:#666;margin:5px 0;">{COMPANY_SLOGAN}</p>
            </div>
            
            <h2 style="color:#333;">Merci pour votre achat! 🎉</h2>
            
            <p>Bonjour {invoice['client_name']},</p>
            <p>Nous vous remercions pour votre achat chez {COMPANY_NAME}.</p>
            
            <div style="background:#f9f9f9;padding:20px;border-radius:10px;margin:20px 0;">
                <h3 style="margin-top:0;">Facture {invoice['number']}</h3>
                <p>Date: {invoice['date_invoice'][:10] if invoice['date_invoice'] else ''}</p>
                
                <table style="width:100%;border-collapse:collapse;margin:15px 0;">
                    <tr style="background:{KRYSTO_PRIMARY};color:white;">
                        <th style="padding:10px;text-align:left;">Article</th>
                        <th style="padding:10px;text-align:center;">Qté</th>
                        <th style="padding:10px;text-align:right;">Total</th>
                    </tr>
                    {lines_html}
                </table>
                
                <div style="text-align:right;margin-top:15px;">
                    <p>Sous-total: {format_price(invoice['subtotal'])}</p>
                    <p>TGC ({tgc_percent}%): {format_price(invoice['tgc_amount'])}</p>
                    <p style="font-size:18px;font-weight:bold;color:{KRYSTO_PRIMARY};">
                        TOTAL: {format_price(invoice['total'])}
                    </p>
                </div>
            </div>
            
            <p>À bientôt chez {COMPANY_NAME}!</p>
            
            <div style="margin-top:30px;padding-top:20px;border-top:1px solid #eee;text-align:center;color:#888;">
                <p>{COMPANY_ADDRESS}</p>
                <p>{COMPANY_EMAIL} | {COMPANY_PHONE}</p>
            </div>
        </div>
        """
        
        try:
            # Envoyer l'email
            smtp_config = get_smtp_config()
            if not smtp_config.get('smtp_host'):
                print("[CAISSE] Configuration SMTP manquante")
                return
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Votre facture {invoice['number']} - {COMPANY_NAME}"
            msg['From'] = smtp_config.get('smtp_user', COMPANY_EMAIL)
            msg['To'] = invoice['client_email']
            
            msg.attach(MIMEText(html, 'html'))
            
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_config['smtp_host'], smtp_config.get('smtp_port', 465), context=context) as server:
                server.login(smtp_config['smtp_user'], smtp_config['smtp_password'])
                server.send_message(msg)
            
            print(f"[CAISSE] Email envoyé à {invoice['client_email']}")
        except Exception as e:
            print(f"[CAISSE] Erreur envoi email: {e}")
    
    def _load_historique(self):
        """Charge l'historique des ventes."""
        for w in self.historique_list.winfo_children():
            w.destroy()
        
        # Déterminer la période
        period = self.date_filter.get()
        today = datetime.now().strftime('%Y-%m-%d')
        
        if period == "Aujourd'hui":
            sales = get_caisse_sales_by_period(today)
        elif period == "Cette semaine":
            week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
            sales = get_caisse_sales_by_period(week_start, today)
        elif period == "Ce mois":
            month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            sales = get_caisse_sales_by_period(month_start, today)
        else:
            sales = get_all_caisse_sales(200)
        
        # Calculer les totaux de la période
        total_period = sum(s['total'] or 0 for s in sales)
        self.period_stats.configure(text=f"📊 {len(sales)} vente(s) | Total: {format_price(total_period)}")
        
        if not sales:
            ctk.CTkLabel(self.historique_list, text="Aucune vente sur cette période", 
                        text_color="#666").pack(pady=30)
            return
        
        # En-tête
        header = ctk.CTkFrame(self.historique_list, fg_color="#1a1a1a")
        header.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(header, text="Date/Heure", width=140, font=("Helvetica", 10, "bold")).pack(side="left", padx=5, pady=8)
        ctk.CTkLabel(header, text="Client", width=150, font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Facture", width=100, font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Paiement", width=80, font=("Helvetica", 10, "bold")).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Total", width=100, font=("Helvetica", 10, "bold")).pack(side="right", padx=10)
        ctk.CTkLabel(header, text="Ticket Z", width=80, font=("Helvetica", 10, "bold")).pack(side="right", padx=5)
        
        for sale in sales:
            row = ctk.CTkFrame(self.historique_list, fg_color="#2a2a2a" if sales.index(sale) % 2 == 0 else "#333333")
            row.pack(fill="x", pady=1)
            
            # Date
            date_str = sale['date_sale'][:16] if sale['date_sale'] else ""
            ctk.CTkLabel(row, text=date_str, width=140, font=("Helvetica", 10)).pack(side="left", padx=5, pady=6)
            
            # Client
            client_name = sale['client_name'] or "Inconnu"
            ctk.CTkLabel(row, text=client_name[:18], width=150, font=("Helvetica", 10)).pack(side="left", padx=5)
            
            # Facture
            invoice_num = sale['invoice_number'] or "-"
            ctk.CTkLabel(row, text=invoice_num, width=100, font=("Helvetica", 10), text_color="#888").pack(side="left", padx=5)
            
            # Mode de paiement
            payment_icons = {'espèces': '💵', 'carte': '💳', 'autre': '📱'}
            payment = sale['payment_method'] or 'espèces'
            ctk.CTkLabel(row, text=f"{payment_icons.get(payment, '💰')} {payment}", width=80, 
                        font=("Helvetica", 10)).pack(side="left", padx=5)
            
            # Total
            ctk.CTkLabel(row, text=format_price(sale['total'] or 0), width=100, 
                        font=("Helvetica", 10, "bold"), text_color=KRYSTO_SECONDARY).pack(side="right", padx=10)
            
            # Ticket Z
            tz_num = sale['ticket_z_number'] if 'ticket_z_number' in sale.keys() and sale['ticket_z_number'] else "-"
            tz_color = KRYSTO_SECONDARY if tz_num != "-" else "#666"
            ctk.CTkLabel(row, text=f"Z{tz_num}" if tz_num != "-" else "-", width=80, 
                        font=("Helvetica", 10), text_color=tz_color).pack(side="right", padx=5)
    
    def _load_tickets_z(self):
        """Charge la liste des tickets Z."""
        for w in self.tickets_z_list.winfo_children():
            w.destroy()
        
        tickets = get_all_tickets_z()
        
        if not tickets:
            ctk.CTkLabel(self.tickets_z_list, text="Aucun ticket Z généré", 
                        text_color="#666").pack(pady=30)
            return
        
        for ticket in tickets:
            t = dict(ticket)
            
            frame = ctk.CTkFrame(self.tickets_z_list, fg_color="#2a2a2a", corner_radius=10)
            frame.pack(fill="x", pady=5, padx=5)
            
            # Header du ticket
            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=10)
            
            ctk.CTkLabel(header, text=f"🧾 TICKET Z N°{t['number']}", 
                        font=("Helvetica", 14, "bold")).pack(side="left")
            
            date_close = t['date_close'][:16] if t['date_close'] else ""
            ctk.CTkLabel(header, text=date_close, text_color="#888", 
                        font=("Helvetica", 11)).pack(side="right")
            
            # Détails
            details = ctk.CTkFrame(frame, fg_color="#1a1a1a", corner_radius=5)
            details.pack(fill="x", padx=15, pady=(0, 15))
            
            row1 = ctk.CTkFrame(details, fg_color="transparent")
            row1.pack(fill="x", padx=15, pady=10)
            
            ctk.CTkLabel(row1, text=f"📊 {t['nb_sales']} vente(s)", font=("Helvetica", 11)).pack(side="left", padx=10)
            ctk.CTkLabel(row1, text=f"💵 Espèces: {format_price(t['total_especes'] or 0)}", 
                        font=("Helvetica", 11)).pack(side="left", padx=10)
            ctk.CTkLabel(row1, text=f"💳 Carte: {format_price(t['total_carte'] or 0)}", 
                        font=("Helvetica", 11)).pack(side="left", padx=10)
            ctk.CTkLabel(row1, text=f"📱 Autre: {format_price(t['total_autre'] or 0)}", 
                        font=("Helvetica", 11)).pack(side="left", padx=10)
            
            row2 = ctk.CTkFrame(details, fg_color="transparent")
            row2.pack(fill="x", padx=15, pady=(0, 10))
            
            ctk.CTkLabel(row2, text=f"HT: {format_price(t['total_ht'] or 0)}", 
                        font=("Helvetica", 10), text_color="#888").pack(side="left", padx=10)
            ctk.CTkLabel(row2, text=f"TGC: {format_price(t['total_tgc'] or 0)}", 
                        font=("Helvetica", 10), text_color="#888").pack(side="left", padx=10)
            ctk.CTkLabel(row2, text=f"TOTAL TTC: {format_price(t['total_ttc'] or 0)}", 
                        font=("Helvetica", 12, "bold"), text_color=KRYSTO_SECONDARY).pack(side="right", padx=10)
            
            # Bouton voir détails
            ctk.CTkButton(frame, text="📋 Voir ventes", fg_color=KRYSTO_PRIMARY, width=100, height=28,
                         command=lambda tid=t['id']: self._show_ticket_z_details(tid)).pack(anchor="e", padx=15, pady=(0, 10))
    
    def _show_ticket_z_details(self, ticket_id):
        """Affiche les détails d'un ticket Z."""
        ticket = get_ticket_z(ticket_id)
        sales = get_caisse_sales_by_ticket_z(ticket_id)
        
        if not ticket:
            return
        
        t = dict(ticket)
        
        # Créer une fenêtre popup
        popup = ctk.CTkToplevel(self)
        popup.title(f"Ticket Z N°{t['number']}")
        popup.geometry("700x500")
        popup.transient(self)
        popup.grab_set()
        
        # Header
        header = ctk.CTkFrame(popup, fg_color=KRYSTO_DARK)
        header.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(header, text=f"🧾 TICKET Z N°{t['number']}", 
                    font=("Helvetica", 18, "bold")).pack(pady=15)
        ctk.CTkLabel(header, text=f"Clôturé le: {t['date_close'][:16] if t['date_close'] else ''}", 
                    text_color="#888").pack(pady=(0, 15))
        
        # Résumé
        summary = ctk.CTkFrame(popup, fg_color="#2a2a2a")
        summary.pack(fill="x", padx=20, pady=10)
        
        row = ctk.CTkFrame(summary, fg_color="transparent")
        row.pack(pady=15)
        
        for label, value, color in [
            ("Ventes", str(t['nb_sales']), "#fff"),
            ("Espèces", format_price(t['total_especes'] or 0), "#28a745"),
            ("Carte", format_price(t['total_carte'] or 0), "#17a2b8"),
            ("Autre", format_price(t['total_autre'] or 0), "#6c5ce7"),
            ("TOTAL", format_price(t['total_ttc'] or 0), KRYSTO_SECONDARY)
        ]:
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", padx=20)
            ctk.CTkLabel(col, text=label, text_color="#888", font=("Helvetica", 10)).pack()
            ctk.CTkLabel(col, text=value, text_color=color, font=("Helvetica", 14, "bold")).pack()
        
        # Liste des ventes
        ctk.CTkLabel(popup, text="📋 Détail des ventes", font=("Helvetica", 13, "bold")).pack(anchor="w", padx=25, pady=(15, 5))
        
        sales_list = ctk.CTkScrollableFrame(popup, fg_color="#2a2a2a")
        sales_list.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        for sale in sales:
            s = dict(sale)
            srow = ctk.CTkFrame(sales_list, fg_color="#1a1a1a")
            srow.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(srow, text=s['date_sale'][:16] if s['date_sale'] else "", 
                        width=130, font=("Helvetica", 10)).pack(side="left", padx=5, pady=6)
            ctk.CTkLabel(srow, text=s['client_name'] or "N/A", width=150, 
                        font=("Helvetica", 10)).pack(side="left", padx=5)
            
            payment_icons = {'espèces': '💵', 'carte': '💳', 'autre': '📱'}
            payment = s['payment_method'] or 'espèces'
            ctk.CTkLabel(srow, text=payment_icons.get(payment, '💰'), 
                        font=("Helvetica", 10)).pack(side="left", padx=5)
            
            ctk.CTkLabel(srow, text=format_price(s['total'] or 0), 
                        font=("Helvetica", 10, "bold"), text_color=KRYSTO_SECONDARY).pack(side="right", padx=10)
    
    def _generate_ticket_z(self):
        """Génère le ticket Z (clôture de caisse)."""
        stats = get_caisse_stats_today()
        
        if stats['nb_sales'] == 0:
            messagebox.showinfo("Ticket Z", "Aucune vente à clôturer aujourd'hui.")
            return
        
        # Confirmation
        msg = f"""Clôturer la caisse ?

📊 Ventes du jour: {stats['nb_sales']}
💵 Espèces: {format_price(stats['total_especes'])}
💳 Carte: {format_price(stats['total_carte'])}
📱 Autre: {format_price(stats['total_autre'])}

💰 TOTAL: {format_price(stats['total_ttc'])}

Cette action est irréversible."""
        
        if not messagebox.askyesno("Ticket Z - Clôture de caisse", msg):
            return
        
        # Générer le ticket Z
        ticket_id, result = close_ticket_z()
        
        if ticket_id is None:
            messagebox.showerror("Erreur", str(result))
            return
        
        # Afficher le résultat
        messagebox.showinfo("Ticket Z généré", 
            f"""✅ TICKET Z N°{result['number']} GÉNÉRÉ

📊 {result['nb_sales']} vente(s) clôturée(s)

💵 Espèces: {format_price(result['total_especes'])}
💳 Carte: {format_price(result['total_carte'])}
📱 Autre: {format_price(result['total_autre'])}

💰 TOTAL TTC: {format_price(result['total_ttc'])}

Caisse clôturée avec succès!""")
        
        # Rafraîchir les affichages
        self._update_stats()
        self._load_historique()
        self._load_tickets_z()


class CaisseClientDialog(ctk.CTkToplevel):
    """Dialogue de création rapide de client depuis la caisse."""
    
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.on_save = on_save
        self.title("👤 Nouveau client")
        self.geometry("450x500")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main, text="Créer un nouveau client", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
        
        ctk.CTkLabel(main, text="Nom *").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(main, height=38)
        self.name_entry.pack(fill="x", pady=(0, 10))
        self.name_entry.focus()
        
        ctk.CTkLabel(main, text="Email (pour recevoir la facture)").pack(anchor="w")
        self.email_entry = ctk.CTkEntry(main, height=38, placeholder_text="email@exemple.com")
        self.email_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main, text="Téléphone").pack(anchor="w")
        self.phone_entry = ctk.CTkEntry(main, height=38, placeholder_text="+687...")
        self.phone_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main, text="Adresse").pack(anchor="w")
        self.address_entry = ctk.CTkEntry(main, height=38)
        self.address_entry.pack(fill="x", pady=(0, 15))
        
        # Newsletter
        self.newsletter_var = ctk.BooleanVar(value=True)
        newsletter_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK, corner_radius=10)
        newsletter_frame.pack(fill="x", pady=10)
        
        ctk.CTkCheckBox(newsletter_frame, text="📧 S'inscrire à la newsletter", 
                        variable=self.newsletter_var,
                        font=("Helvetica", 12)).pack(anchor="w", padx=15, pady=15)
        
        ctk.CTkLabel(newsletter_frame, text="Recevoir nos offres et actualités par email",
                     text_color="#888", font=("Helvetica", 10)).pack(anchor="w", padx=15, pady=(0, 15))
        
        # Boutons
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(btn_frame, text="Annuler", fg_color="gray", width=100,
                      command=self.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text="✅ Créer le client", fg_color=KRYSTO_PRIMARY, width=150,
                      command=self._save).pack(side="right")
    
    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Attention", "Le nom est obligatoire")
            return
        
        email = self.email_entry.get().strip()
        if email and '@' not in email:
            messagebox.showwarning("Attention", "Email invalide")
            return
        
        data = {
            'name': name,
            'email': email,
            'phone': self.phone_entry.get().strip(),
            'address': self.address_entry.get().strip(),
            'client_type': 'particulier',
            'newsletter': 1 if self.newsletter_var.get() else 0,
            'is_prospect': 0  # Client direct, pas prospect
        }
        
        client_id = save_client(data)
        
        messagebox.showinfo("Succès", f"Client '{name}' créé!" + 
                           ("\n📧 Inscrit à la newsletter" if self.newsletter_var.get() else ""))
        
        if self.on_save:
            self.on_save(client_id)
        
        self.destroy()


# ============================================================================
# DASHBOARD
# ============================================================================
class DashboardFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._create_ui()
    
    def _create_ui(self):
        # Header avec date et bouton refresh
        header = ctk.CTkFrame(self, fg_color=KRYSTO_DARK, corner_radius=10)
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text=f"🏭 {COMPANY_NAME}", font=("Helvetica", 22, "bold")).pack(side="left", padx=20, pady=15)
        ctk.CTkButton(header, text="🔄 Actualiser", fg_color=KRYSTO_PRIMARY, width=100,
                      command=self._refresh).pack(side="right", padx=10, pady=10)
        ctk.CTkLabel(header, text=datetime.now().strftime("%A %d/%m/%Y"), text_color="#888").pack(side="right", padx=10)
        
        # Conteneur principal scrollable
        main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # KPIs principaux
        self.stats_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        self.stats_frame.pack(fill="x", pady=5)
        
        # Tâches du jour
        self.tasks_frame = ctk.CTkFrame(main_scroll, fg_color=KRYSTO_DARK, corner_radius=10)
        self.tasks_frame.pack(fill="x", pady=5, padx=5)
        
        # Actions rapides
        self.actions_frame = ctk.CTkFrame(main_scroll, fg_color=KRYSTO_DARK, corner_radius=10)
        self.actions_frame.pack(fill="x", pady=5, padx=5)
        
        # Deux colonnes : Impayés + Factures récentes
        bottom = ctk.CTkFrame(main_scroll, fg_color="transparent")
        bottom.pack(fill="both", expand=True, pady=5)
        
        # Colonne gauche - Impayés
        self.debts_frame = ctk.CTkFrame(bottom, fg_color=KRYSTO_DARK, corner_radius=10)
        self.debts_frame.pack(side="left", fill="both", expand=True, padx=(5, 2))
        
        # Colonne droite - Activité récente
        self.activity_frame = ctk.CTkFrame(bottom, fg_color=KRYSTO_DARK, corner_radius=10)
        self.activity_frame.pack(side="right", fill="both", expand=True, padx=(2, 5))
        
        self._refresh()
    
    def _refresh(self):
        """Actualise tout le dashboard."""
        self._load_stats()
        self._load_tasks()
        self._load_actions()
        self._load_debts()
        self._load_activity()
    
    def _load_stats(self):
        for w in self.stats_frame.winfo_children(): w.destroy()
        
        stats = get_dashboard_stats()
        
        kpis = [
            ("👥", "Clients", stats['total_clients'], KRYSTO_PRIMARY),
            ("🎯", "Prospects", stats['total_prospects'], "#f39c12"),
            ("📧", "Newsletter", stats['total_newsletter'], KRYSTO_SECONDARY),
            ("💰", "CA Mois", format_price(stats['revenue_month']), "#28a745"),
            ("🚫", "Impayés", format_price(stats['total_debt']), "#dc3545"),
            ("📋", "Tâches", stats['tasks_pending'], "#6c5ce7"),
        ]
        
        for icon, title, val, color in kpis:
            card = ctk.CTkFrame(self.stats_frame, fg_color=KRYSTO_DARK, corner_radius=10)
            card.pack(side="left", fill="both", expand=True, padx=3)
            ctk.CTkLabel(card, text=icon, font=("Helvetica", 24)).pack(pady=(12, 3))
            ctk.CTkLabel(card, text=str(val), font=("Helvetica", 18, "bold"), text_color=color).pack()
            ctk.CTkLabel(card, text=title, text_color="#888", font=("Helvetica", 10)).pack(pady=(0, 12))
    
    def _load_tasks(self):
        for w in self.tasks_frame.winfo_children(): w.destroy()
        
        tasks = get_tasks_due_today()
        
        header = ctk.CTkFrame(self.tasks_frame, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(header, text=f"📋 Tâches du jour ({len(tasks)})", font=("Helvetica", 13, "bold")).pack(side="left")
        
        if not tasks:
            ctk.CTkLabel(self.tasks_frame, text="✅ Aucune tâche en retard!", text_color=KRYSTO_SECONDARY).pack(pady=10)
        else:
            for task in tasks[:5]:
                row = ctk.CTkFrame(self.tasks_frame, fg_color="#2a2a2a")
                row.pack(fill="x", padx=10, pady=2)
                
                priority_colors = {'haute': '#dc3545', 'normale': '#17a2b8', 'basse': '#28a745'}
                priority = task['priority'] or 'normale'
                
                ctk.CTkLabel(row, text="•", text_color=priority_colors.get(priority, '#888'), 
                             font=("Helvetica", 16, "bold")).pack(side="left", padx=(10, 5), pady=6)
                ctk.CTkLabel(row, text=task['title'][:40], font=("Helvetica", 11)).pack(side="left", pady=6)
                
                if task['client_name']:
                    ctk.CTkLabel(row, text=f"👤 {task['client_name']}", text_color="#888", 
                                 font=("Helvetica", 9)).pack(side="right", padx=10)
    
    def _load_actions(self):
        for w in self.actions_frame.winfo_children(): w.destroy()
        
        ctk.CTkLabel(self.actions_frame, text="⚡ Actions rapides", font=("Helvetica", 13, "bold")).pack(side="left", padx=15, pady=10)
        
        ctk.CTkButton(self.actions_frame, text="👤 Nouveau client", fg_color=KRYSTO_PRIMARY, width=130,
                      command=self._new_client).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(self.actions_frame, text="📝 Nouveau devis", fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK, width=130,
                      command=self._new_quote).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(self.actions_frame, text="📋 Nouvelle tâche", fg_color="#6c5ce7", width=130,
                      command=self._new_task).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(self.actions_frame, text="🔄 Rotation dettes", fg_color="gray", width=130,
                      command=self._manual_rotate_debts).pack(side="left", padx=5, pady=10)
        
        self.action_status = ctk.CTkLabel(self.actions_frame, text="✅ Auto-tâches actives",
                                          text_color=KRYSTO_SECONDARY, font=("Helvetica", 9))
        self.action_status.pack(side="right", padx=15)
    
    def _load_debts(self):
        for w in self.debts_frame.winfo_children(): w.destroy()
        
        ctk.CTkLabel(self.debts_frame, text="💰 Impayés Pro", 
                     font=("Helvetica", 13, "bold")).pack(anchor="w", padx=15, pady=10)
        
        clients_debt = get_all_clients(client_type="professionnel", with_debt=True)
        
        if not clients_debt:
            ctk.CTkLabel(self.debts_frame, text="🎉 Aucun impayé!", text_color=KRYSTO_SECONDARY).pack(pady=15)
        else:
            for c in clients_debt[:8]:
                row = ctk.CTkFrame(self.debts_frame, fg_color="#2a2a2a")
                row.pack(fill="x", padx=10, pady=2)
                
                bloque = c['bloque'] if 'bloque' in c.keys() else 0
                name = c['name'] if 'name' in c.keys() else "?"
                
                if bloque:
                    ctk.CTkLabel(row, text="🚫", font=("Helvetica", 10)).pack(side="left", padx=(8, 2), pady=6)
                
                ctk.CTkLabel(row, text=name[:20], font=("Helvetica", 11)).pack(side="left", padx=8, pady=6)
                
                m1 = c['dette_m1'] if 'dette_m1' in c.keys() else 0
                m2 = c['dette_m2'] if 'dette_m2' in c.keys() else 0
                m3 = c['dette_m3'] if 'dette_m3' in c.keys() else 0
                m3p = c['dette_m3plus'] if 'dette_m3plus' in c.keys() else 0
                total = (m1 or 0) + (m2 or 0) + (m3 or 0) + (m3p or 0)
                
                color = "#dc3545" if m3p else ("#f39c12" if m3 else "#ffc107")
                ctk.CTkLabel(row, text=format_price(total), text_color=color,
                             font=("Helvetica", 11, "bold")).pack(side="right", padx=10)
    
    def _load_activity(self):
        for w in self.activity_frame.winfo_children(): w.destroy()
        
        ctk.CTkLabel(self.activity_frame, text="📊 Activité récente", 
                     font=("Helvetica", 13, "bold")).pack(anchor="w", padx=15, pady=10)
        
        # Dernières interactions
        interactions = get_all_interactions(limit=5)
        
        if not interactions:
            ctk.CTkLabel(self.activity_frame, text="Aucune activité récente", text_color="#666").pack(pady=15)
        else:
            for inter in interactions:
                row = ctk.CTkFrame(self.activity_frame, fg_color="#2a2a2a")
                row.pack(fill="x", padx=10, pady=2)
                
                ctk.CTkLabel(row, text=inter['type'][:2], font=("Helvetica", 10)).pack(side="left", padx=8, pady=6)
                
                text = f"{inter['client_name'] or 'N/A'}"
                if inter['subject']:
                    text += f" - {inter['subject'][:20]}"
                ctk.CTkLabel(row, text=text, font=("Helvetica", 10)).pack(side="left", pady=6)
                
                date_str = inter['date_interaction'][:10] if inter['date_interaction'] else ""
                ctk.CTkLabel(row, text=date_str, text_color="#666", font=("Helvetica", 9)).pack(side="right", padx=10)
    
    def _new_client(self):
        ClientDialog(self, on_save=self._refresh)
    
    def _new_quote(self):
        QuoteEditorDialog(self, on_save=self._refresh)
    
    def _new_task(self):
        TaskEditorDialog(self, on_save=self._refresh)
    
    def _manual_rotate_debts(self):
        """Déclenche manuellement la rotation des dettes."""
        rotations = rotate_debts()
        if rotations > 0:
            messagebox.showinfo("Rotation", f"{rotations} rotation(s) effectuée(s).")
            self._refresh()
        else:
            messagebox.showinfo("Rotation", "Aucune dette à faire tourner.")


class ConfigDialog(ctk.CTkToplevel):
    """Dialogue de configuration des couleurs et infos entreprise."""
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.on_save = on_save
        self.title("⚙️ Configuration")
        self.geometry("500x700")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        # Boutons en bas
        btn_frame = ctk.CTkFrame(self, fg_color="#2a2a2a", height=60)
        btn_frame.pack(fill="x", side="bottom")
        btn_frame.pack_propagate(False)
        ctk.CTkButton(btn_frame, text="❌ Annuler", fg_color="#666", width=120, command=self.destroy).pack(side="left", padx=20, pady=10)
        ctk.CTkButton(btn_frame, text="💾 Sauvegarder", fg_color=KRYSTO_PRIMARY, width=150, command=self._save).pack(side="right", padx=20, pady=10)
        
        # Contenu scrollable
        container = ctk.CTkScrollableFrame(self)
        container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Section Entreprise
        ctk.CTkLabel(container, text="🏢 Informations Entreprise", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
        
        fields = [
            ("Nom entreprise:", "company_name", COMPANY_NAME),
            ("Slogan:", "company_slogan", COMPANY_SLOGAN),
            ("Adresse:", "company_address", COMPANY_ADDRESS),
            ("Email:", "company_email", COMPANY_EMAIL),
            ("Site web:", "company_website", COMPANY_WEBSITE),
            ("Téléphone:", "company_phone", COMPANY_PHONE),
            ("N° RIDET:", "company_ridet", COMPANY_RIDET),
        ]
        
        self.entries = {}
        for label, key, default in fields:
            row = ctk.CTkFrame(container, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=label, width=120, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row)
            entry.pack(side="left", fill="x", expand=True, padx=5)
            entry.insert(0, default)
            self.entries[key] = entry
        
        # Section Couleurs
        ctk.CTkLabel(container, text="🎨 Couleurs", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(25, 15))
        
        colors_frame = ctk.CTkFrame(container, fg_color="#2a2a2a")
        colors_frame.pack(fill="x", pady=10)
        
        self.color_btns = {}
        color_config = [
            ("Primaire", "primary", KRYSTO_PRIMARY),
            ("Secondaire", "secondary", KRYSTO_SECONDARY),
            ("Sombre", "dark", KRYSTO_DARK),
            ("Clair", "light", KRYSTO_LIGHT),
        ]
        
        for label, key, color in color_config:
            row = ctk.CTkFrame(colors_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=8)
            ctk.CTkLabel(row, text=label, width=100, anchor="w").pack(side="left")
            
            btn = ctk.CTkButton(row, text="", width=50, height=30, fg_color=color, hover_color=color,
                               command=lambda k=key: self._pick_color(k))
            btn.pack(side="left", padx=10)
            self.color_btns[key] = btn
            
            entry = ctk.CTkEntry(row, width=100)
            entry.insert(0, color)
            entry.pack(side="left")
            self.entries[key] = entry
            
            # Lier l'entrée au bouton
            entry.bind("<FocusOut>", lambda e, k=key: self._update_color_btn(k))
        
        # Preview couleurs
        ctk.CTkLabel(container, text="📌 Aperçu", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(20, 10))
        self.preview_frame = ctk.CTkFrame(container, height=80)
        self.preview_frame.pack(fill="x", pady=5)
        self._update_preview()
        
        # Info
        ctk.CTkLabel(container, text="💡 Les changements seront appliqués au prochain démarrage de l'application",
                     text_color="#888", font=("Helvetica", 10)).pack(anchor="w", pady=(15, 0))
    
    def _pick_color(self, key):
        current = self.entries[key].get()
        dialog = ColorPickerDialog(self, current)
        self.wait_window(dialog)
        if dialog.result:
            self.entries[key].delete(0, "end")
            self.entries[key].insert(0, dialog.result)
            self.color_btns[key].configure(fg_color=dialog.result, hover_color=dialog.result)
            self._update_preview()
    
    def _update_color_btn(self, key):
        color = self.entries[key].get()
        if color.startswith("#") and len(color) in [4, 7]:
            self.color_btns[key].configure(fg_color=color, hover_color=color)
            self._update_preview()
    
    def _update_preview(self):
        # Clear preview
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        primary = self.entries.get('primary', {})
        secondary = self.entries.get('secondary', {})
        dark = self.entries.get('dark', {})
        
        p_color = primary.get() if hasattr(primary, 'get') else KRYSTO_PRIMARY
        s_color = secondary.get() if hasattr(secondary, 'get') else KRYSTO_SECONDARY
        d_color = dark.get() if hasattr(dark, 'get') else KRYSTO_DARK
        
        ctk.CTkFrame(self.preview_frame, width=80, height=60, fg_color=p_color, corner_radius=8).pack(side="left", padx=10, pady=10)
        ctk.CTkFrame(self.preview_frame, width=80, height=60, fg_color=s_color, corner_radius=8).pack(side="left", padx=10, pady=10)
        ctk.CTkFrame(self.preview_frame, width=80, height=60, fg_color=d_color, corner_radius=8).pack(side="left", padx=10, pady=10)
    
    def _save(self):
        global COMPANY_NAME, COMPANY_ADDRESS, COMPANY_EMAIL, COMPANY_WEBSITE, COMPANY_PHONE, COMPANY_RIDET, COMPANY_SLOGAN
        global KRYSTO_PRIMARY, KRYSTO_SECONDARY, KRYSTO_DARK, KRYSTO_LIGHT
        
        # Mettre à jour les variables globales
        COMPANY_NAME = self.entries['company_name'].get()
        COMPANY_SLOGAN = self.entries['company_slogan'].get()
        COMPANY_ADDRESS = self.entries['company_address'].get()
        COMPANY_EMAIL = self.entries['company_email'].get()
        COMPANY_WEBSITE = self.entries['company_website'].get()
        COMPANY_PHONE = self.entries['company_phone'].get()
        COMPANY_RIDET = self.entries['company_ridet'].get()
        
        KRYSTO_PRIMARY = self.entries['primary'].get()
        KRYSTO_SECONDARY = self.entries['secondary'].get()
        KRYSTO_DARK = self.entries['dark'].get()
        KRYSTO_LIGHT = self.entries['light'].get()
        
        # Sauvegarder
        save_colors_config()
        
        messagebox.showinfo("Sauvegardé", "Configuration sauvegardée!\n\nRedémarrez l'application pour appliquer les couleurs.")
        
        if self.on_save:
            self.on_save()
        self.destroy()


# ============================================================================
# APPLICATION PRINCIPALE
# ============================================================================
class KrystoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{COMPANY_NAME} - v8.3")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        init_database()
        self._create_ui()
        
        # Démarrer les tâches automatiques
        self._start_auto_tasks()
        
        # Raccourcis clavier
        self.bind("<Control-n>", lambda e: self._quick_action("new_client"))
        self.bind("<Control-f>", lambda e: self._show_search())
        self.bind("<Control-b>", lambda e: self._backup_now())
    
    def _start_auto_tasks(self):
        """Démarre les tâches automatiques en arrière-plan."""
        def auto_tasks():
            import time
            while True:
                try:
                    # Rotation des dettes tous les jours
                    rotations = rotate_debts()
                    if rotations > 0:
                        print(f"[AUTO] {rotations} rotation(s) de dettes effectuée(s)")
                    
                    # Vérifier si on est le 1er du mois à 9h pour envoyer les rappels
                    now = datetime.now()
                    if now.day == 1 and now.hour == 9 and now.minute < 5:
                        print("[AUTO] Envoi des rappels mensuels d'impayés...")
                        results = send_monthly_debt_reminders()
                        print(f"[AUTO] Rappels envoyés: {results['sent']}, Erreurs: {len(results['errors'])}")
                    
                    # Vérifier les emails programmés
                    sent = check_and_send_scheduled_emails()
                    if sent > 0:
                        print(f"[AUTO] {sent} email(s) programmé(s) envoyé(s)")
                    
                except Exception as e:
                    print(f"[AUTO] Erreur: {e}")
                
                # Attendre 5 minutes avant la prochaine vérification
                time.sleep(300)
        
        # Lancer en thread daemon (s'arrête quand l'app se ferme)
        thread = threading.Thread(target=auto_tasks, daemon=True)
        thread.start()
        
        # Exécuter rotation immédiate au démarrage
        self.after(2000, self._run_startup_tasks)
    
    def _run_startup_tasks(self):
        """Tâches à exécuter au démarrage."""
        try:
            rotations = rotate_debts()
            if rotations > 0:
                print(f"[STARTUP] {rotations} rotation(s) de dettes effectuée(s)")
        except Exception as e:
            print(f"[STARTUP] Erreur rotation dettes: {e}")
    
    def _create_ui(self):
        sidebar = ctk.CTkFrame(self, width=200, fg_color=KRYSTO_DARK, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        logo = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo.pack(fill="x", pady=20)
        ctk.CTkLabel(logo, text="♻️", font=("Helvetica", 36)).pack()
        ctk.CTkLabel(logo, text=COMPANY_NAME, font=("Helvetica", 22, "bold")).pack()
        ctk.CTkLabel(logo, text=COMPANY_SLOGAN, text_color="#888", font=("Helvetica", 9)).pack()
        
        # Menu principal avec tous les modules
        menu_items = [
            ("🏠", "Tableau de bord", "dashboard"),
            ("🛒", "Caisse", "caisse"),
            ("📊", "Statistiques", "stats"),
            ("👥", "Clients", "clients"),
            ("📄", "Devis/Factures", "invoices"),
            ("🎯", "CRM", "crm"),
            ("📦", "Produits", "products"),
            ("🏪", "Dépôts-Ventes", "depots"),
            ("📧", "Mailing", "mailing"),
        ]
        
        self.menu_buttons = {}
        for icon, label, key in menu_items:
            btn = ctk.CTkButton(sidebar, text=f"  {icon}  {label}", anchor="w", height=40, fg_color="transparent",
                                hover_color="#3a3a3a", font=("Helvetica", 12), command=lambda k=key: self._show_frame(k))
            btn.pack(fill="x", padx=10, pady=2)
            self.menu_buttons[key] = btn
        
        # Section utilitaires en bas
        utils_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        utils_frame.pack(side="bottom", fill="x", pady=10)
        
        ctk.CTkButton(utils_frame, text="🔍 Recherche", anchor="w", height=32, fg_color="transparent",
                      hover_color="#3a3a3a", font=("Helvetica", 10), command=self._show_search).pack(fill="x", padx=10, pady=1)
        ctk.CTkButton(utils_frame, text="💾 Sauvegarde", anchor="w", height=32, fg_color="transparent",
                      hover_color="#3a3a3a", font=("Helvetica", 10), command=self._backup_now).pack(fill="x", padx=10, pady=1)
        ctk.CTkButton(utils_frame, text="📥 Import/Export", anchor="w", height=32, fg_color="transparent",
                      hover_color="#3a3a3a", font=("Helvetica", 10), command=self._show_import_export).pack(fill="x", padx=10, pady=1)
        ctk.CTkButton(utils_frame, text="⚙️ Configuration", anchor="w", height=32, fg_color="transparent",
                      hover_color="#3a3a3a", font=("Helvetica", 10), command=self._open_config).pack(fill="x", padx=10, pady=1)
        
        ctk.CTkLabel(utils_frame, text=f"v8.3 | Ctrl+F: Recherche", text_color="#555", font=("Helvetica", 8)).pack(pady=5)
        
        self.main_container = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0)
        self.main_container.pack(side="left", fill="both", expand=True)
        
        self.frames = {
            "dashboard": DashboardFrame(self.main_container),
            "caisse": CaisseFrame(self.main_container),
            "stats": StatistiquesFrame(self.main_container),
            "clients": ClientsFrame(self.main_container),
            "invoices": DevisFacturesFrame(self.main_container),
            "crm": CRMFrame(self.main_container),
            "products": ProductsFrame(self.main_container),
            "depots": DepotsFrame(self.main_container),
            "mailing": MailingFrame(self.main_container),
        }
        
        self._show_frame("dashboard")
    
    def _open_config(self):
        ConfigDialog(self)
    
    def _show_frame(self, key):
        for f in self.frames.values(): f.pack_forget()
        for k, btn in self.menu_buttons.items():
            btn.configure(fg_color=KRYSTO_PRIMARY if k == key else "transparent")
        self.frames[key].pack(fill="both", expand=True)
    
    def _quick_action(self, action):
        """Actions rapides via raccourcis clavier."""
        if action == "new_client":
            self._show_frame("clients")
            ClientDialog(self, on_save=lambda: self.frames["clients"]._load_clients())
    
    def _show_search(self):
        """Affiche la recherche globale."""
        SearchDialog(self)
    
    def _backup_now(self):
        """Sauvegarde immédiate."""
        success, msg = backup_database()
        if success:
            messagebox.showinfo("Sauvegarde", msg)
        else:
            messagebox.showerror("Erreur", msg)
    
    def _show_import_export(self):
        """Affiche le dialogue import/export."""
        ImportExportDialog(self)


class SearchDialog(ctk.CTkToplevel):
    """Recherche globale."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🔍 Recherche globale")
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=20)
        
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Rechercher clients, produits...", height=40)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda e: self._search())
        self.search_entry.bind("<KeyRelease>", lambda e: self._search())
        
        ctk.CTkButton(search_frame, text="🔍", width=50, height=40, command=self._search).pack(side="left", padx=5)
        
        self.results_frame = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.search_entry.focus()
    
    def _search(self):
        query = self.search_entry.get().strip().lower()
        for w in self.results_frame.winfo_children(): w.destroy()
        
        if len(query) < 2:
            ctk.CTkLabel(self.results_frame, text="Tapez au moins 2 caractères", text_color="#666").pack(pady=20)
            return
        
        # Recherche clients
        conn = get_connection()
        clients = conn.execute("SELECT * FROM clients WHERE LOWER(name) LIKE ? OR LOWER(email) LIKE ? LIMIT 10",
                               (f"%{query}%", f"%{query}%")).fetchall()
        
        # Recherche produits
        products = conn.execute("SELECT * FROM products WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? LIMIT 10",
                                (f"%{query}%", f"%{query}%")).fetchall()
        conn.close()
        
        if not clients and not products:
            ctk.CTkLabel(self.results_frame, text="Aucun résultat", text_color="#666").pack(pady=20)
            return
        
        if clients:
            ctk.CTkLabel(self.results_frame, text="👥 Clients", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=10)
            for c in clients:
                frame = ctk.CTkFrame(self.results_frame, fg_color="#2a2a2a")
                frame.pack(fill="x", pady=2)
                ctk.CTkLabel(frame, text=f"{c['name']} - {c['email'] or 'Pas d\'email'}", 
                             font=("Helvetica", 11)).pack(anchor="w", padx=15, pady=8)
        
        if products:
            ctk.CTkLabel(self.results_frame, text="📦 Produits", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=10)
            for p in products:
                frame = ctk.CTkFrame(self.results_frame, fg_color="#2a2a2a")
                frame.pack(fill="x", pady=2)
                ctk.CTkLabel(frame, text=f"{p['name']} - {format_price(p['price'] or 0)}", 
                             font=("Helvetica", 11)).pack(anchor="w", padx=15, pady=8)


class ImportExportDialog(ctk.CTkToplevel):
    """Dialogue import/export."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📥 Import / Export")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        self._create_ui()
    
    def _create_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Export section
        export_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK, corner_radius=10)
        export_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(export_frame, text="📤 Export", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=15, pady=10)
        
        btns = ctk.CTkFrame(export_frame, fg_color="transparent")
        btns.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkButton(btns, text="👥 Clients CSV", fg_color=KRYSTO_PRIMARY,
                      command=self._export_clients).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="📦 Produits CSV", fg_color=KRYSTO_PRIMARY,
                      command=self._export_products).pack(side="left", padx=5)
        
        # Import section
        import_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK, corner_radius=10)
        import_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(import_frame, text="📥 Import", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=15, pady=10)
        
        btns2 = ctk.CTkFrame(import_frame, fg_color="transparent")
        btns2.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkButton(btns2, text="👥 Clients CSV", fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK,
                      command=self._import_clients).pack(side="left", padx=5)
        
        # Backup section
        backup_frame = ctk.CTkFrame(main, fg_color=KRYSTO_DARK, corner_radius=10)
        backup_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(backup_frame, text="💾 Sauvegarde", font=("Helvetica", 14, "bold")).pack(anchor="w", padx=15, pady=10)
        
        btns3 = ctk.CTkFrame(backup_frame, fg_color="transparent")
        btns3.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkButton(btns3, text="💾 Créer sauvegarde", fg_color="#28a745",
                      command=self._create_backup).pack(side="left", padx=5)
        ctk.CTkButton(btns3, text="📂 Restaurer", fg_color="#dc3545",
                      command=self._restore_backup).pack(side="left", padx=5)
        
        ctk.CTkButton(main, text="Fermer", fg_color="gray", command=self.destroy).pack(pady=20)
    
    def _export_clients(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if filepath:
            success, msg = export_clients_csv(filepath)
            messagebox.showinfo("Export", msg) if success else messagebox.showerror("Erreur", msg)
    
    def _export_products(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if filepath:
            success, msg = export_products_csv(filepath)
            messagebox.showinfo("Export", msg) if success else messagebox.showerror("Erreur", msg)
    
    def _import_clients(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if filepath:
            success, msg = import_clients_csv(filepath)
            messagebox.showinfo("Import", msg) if success else messagebox.showerror("Erreur", msg)
    
    def _create_backup(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite", "*.db")])
        if filepath:
            success, msg = backup_database(filepath)
            messagebox.showinfo("Sauvegarde", msg) if success else messagebox.showerror("Erreur", msg)
    
    def _restore_backup(self):
        if not messagebox.askyesno("Attention", "Cette action remplacera toutes les données actuelles. Continuer ?"):
            return
        filepath = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if filepath:
            success, msg = restore_database(filepath)
            if success:
                messagebox.showinfo("Restauration", msg + "\n\nRedémarrez l'application.")
            else:
                messagebox.showerror("Erreur", msg)


if __name__ == "__main__":
    app = KrystoApp()
    app.mainloop()