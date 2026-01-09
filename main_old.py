# #!/usr/bin/env python3
# """
# KRYSTO - Gestionnaire d'Atelier de Recyclage Plastique - Version 5.1
# Avec OF, Fiches PDF, Commandes clients, Maintenance moules, Mailing AMÉLIORÉ
# Devise: XPF (Franc Pacifique)
# """

# import customtkinter as ctk
# from tkinter import filedialog, messagebox, scrolledtext
# from PIL import Image
# import sqlite3
# import os
# import shutil
# from datetime import datetime, timedelta
# import csv
# import smtplib
# import ssl
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from typing import Optional, List, Dict, Any, Tuple
# import threading
# import webbrowser
# import json
# import tempfile

# # ============================================================================
# # CONSTANTES KRYSTO
# # ============================================================================
# COMPANY_NAME = "KRYSTO"
# COMPANY_ADDRESS = "Nouméa, Nouvelle-Calédonie"
# COMPANY_EMAIL = "contact@krysto.io"
# COMPANY_WEBSITE = "www.krysto.io"

# # Charte couleur KRYSTO
# KRYSTO_PRIMARY = "#6d74ab"      # Violet/bleu
# KRYSTO_SECONDARY = "#5cecc8"    # Turquoise
# KRYSTO_DARK = "#343434"         # Noir
# KRYSTO_LIGHT = "#f5f5f5"        # Blanc cassé

# # Fichier config SMTP
# SMTP_CONFIG_FILE = "smtp_config.json"

# # Configuration SMTP par défaut
# DEFAULT_SMTP_CONFIG = {
#     "host": "smtp.hostinger.com",
#     "port": 465,
#     "use_ssl": True,
#     "username": "contact@krysto.io",
#     "password": "",  # À configurer dans l'interface!
#     "from_name": "KRYSTO"
# }

# # Filament
# FILAMENT_RATE_G_H = 84
# FILAMENT_DIAMETER = 1.75
# FILAMENT_DENSITY = 1.24
# SPOOL_WEIGHTS = [250, 500, 750, 1000]
# CURRENCY = "XPF"
# EUR_TO_XPF = 119.33

# # ============================================================================
# # CONFIGURATION CustomTkinter avec charte KRYSTO
# # ============================================================================
# ctk.set_appearance_mode("dark")
# ctk.set_default_color_theme("blue")

# DB_PATH = "krysto_workshop.db"
# IMAGES_DIR = "images"
# BACKUP_DIR = "backups"
# PDF_DIR = "pdf_exports"

# # Imports optionnels
# try:
#     import matplotlib.pyplot as plt
#     from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#     import matplotlib
#     matplotlib.use('TkAgg')
#     HAS_MATPLOTLIB = True
# except ImportError:
#     HAS_MATPLOTLIB = False

# try:
#     from reportlab.lib import colors
#     from reportlab.lib.pagesizes import A4
#     from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
#     from reportlab.lib.units import mm, cm
#     from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
#     from reportlab.pdfgen import canvas
#     HAS_REPORTLAB = True
# except ImportError:
#     HAS_REPORTLAB = False


# # ============================================================================
# # GESTION CONFIG SMTP
# # ============================================================================
# def load_smtp_config():
#     """Charge la config SMTP depuis le fichier JSON."""
#     if os.path.exists(SMTP_CONFIG_FILE):
#         try:
#             with open(SMTP_CONFIG_FILE, 'r') as f:
#                 config = json.load(f)
#                 return {**DEFAULT_SMTP_CONFIG, **config}
#         except:
#             pass
#     return DEFAULT_SMTP_CONFIG.copy()

# def save_smtp_config(config):
#     """Sauvegarde la config SMTP."""
#     try:
#         with open(SMTP_CONFIG_FILE, 'w') as f:
#             json.dump(config, f, indent=2)
#         return True
#     except:
#         return False


# # ============================================================================
# # UTILITAIRES
# # ============================================================================
# def calc_filament_length(weight_g: float) -> float:
#     radius_cm = (FILAMENT_DIAMETER / 2) / 10
#     volume_cm3 = weight_g / FILAMENT_DENSITY
#     area_cm2 = 3.14159 * (radius_cm ** 2)
#     return (volume_cm3 / area_cm2) / 100

# def calc_production_time(weight_g: float, rate: float = FILAMENT_RATE_G_H) -> Dict:
#     hours = weight_g / rate
#     return {
#         'hours': hours,
#         'formatted': f"{int(hours)}h{int((hours % 1) * 60):02d}",
#         'end_time': (datetime.now() + timedelta(hours=hours)).strftime('%H:%M')
#     }

# def format_price(amount: float) -> str:
#     return f"{amount:,.0f} {CURRENCY}"

# def generate_of_number():
#     return f"OF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

# def generate_order_number():
#     return f"CMD-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


# # ============================================================================
# # TEMPLATES EMAIL HTML AMÉLIORÉS
# # ============================================================================
# def get_email_template_simple(subject, content, show_button=True):
#     """Template email simple avec design KRYSTO."""
#     button_html = ""
#     if show_button:
#         button_html = f'''
#         <tr>
#             <td align="center" style="padding: 20px 40px 30px 40px;">
#                 <a href="https://{COMPANY_WEBSITE}" style="display: inline-block; padding: 14px 35px; 
#                    background: linear-gradient(135deg, {KRYSTO_PRIMARY} 0%, {KRYSTO_SECONDARY} 100%); 
#                    color: #ffffff; text-decoration: none; border-radius: 25px; font-weight: bold; font-size: 14px;">
#                    Visitez notre site
#                 </a>
#             </td>
#         </tr>'''
    
#     return f'''<!DOCTYPE html>
# <html lang="fr">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>{subject}</title>
# </head>
# <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
#     <table role="presentation" style="width: 100%; border-collapse: collapse;">
#         <tr>
#             <td align="center" style="padding: 40px 0;">
#                 <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); overflow: hidden;">
                    
#                     <!-- Header avec gradient KRYSTO -->
#                     <tr>
#                         <td style="background: linear-gradient(135deg, {KRYSTO_PRIMARY} 0%, {KRYSTO_SECONDARY} 100%); padding: 35px 40px; text-align: center;">
#                             <div style="font-size: 45px; margin-bottom: 10px;">♻️</div>
#                             <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: bold; letter-spacing: 1px;">{COMPANY_NAME}</h1>
#                             <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">Recyclage Plastique • Nouvelle-Calédonie</p>
#                         </td>
#                     </tr>
                    
#                     <!-- Contenu -->
#                     <tr>
#                         <td style="padding: 40px;">
#                             <h2 style="margin: 0 0 25px 0; color: {KRYSTO_DARK}; font-size: 24px; border-bottom: 3px solid {KRYSTO_SECONDARY}; padding-bottom: 15px;">{subject}</h2>
#                             <div style="color: {KRYSTO_DARK}; font-size: 15px; line-height: 1.8;">
#                                 {content}
#                             </div>
#                         </td>
#                     </tr>
                    
#                     {button_html}
                    
#                     <!-- Séparateur -->
#                     <tr>
#                         <td style="padding: 0 40px;">
#                             <div style="height: 3px; background: linear-gradient(90deg, {KRYSTO_SECONDARY}, {KRYSTO_PRIMARY}, {KRYSTO_SECONDARY}); border-radius: 2px;"></div>
#                         </td>
#                     </tr>
                    
#                     <!-- Footer -->
#                     <tr>
#                         <td style="padding: 30px 40px; background-color: #fafafa;">
#                             <table role="presentation" style="width: 100%;">
#                                 <tr>
#                                     <td style="color: #666666; font-size: 13px;">
#                                         <p style="margin: 0 0 10px 0; font-weight: bold; color: {KRYSTO_PRIMARY};">{COMPANY_NAME}</p>
#                                         <p style="margin: 0 0 5px 0;">📍 {COMPANY_ADDRESS}</p>
#                                         <p style="margin: 0 0 5px 0;">📧 {COMPANY_EMAIL}</p>
#                                         <p style="margin: 0;">🌐 {COMPANY_WEBSITE}</p>
#                                     </td>
#                                     <td align="right" valign="top">
#                                         <p style="margin: 0; color: #999999; font-size: 11px;">
#                                             © {datetime.now().year} {COMPANY_NAME}
#                                         </p>
#                                     </td>
#                                 </tr>
#                             </table>
#                         </td>
#                     </tr>
#                 </table>
                
#                 <!-- Désabonnement -->
#                 <p style="margin: 25px 0 0 0; color: #999999; font-size: 11px;">
#                     Vous recevez cet email car vous êtes client {COMPANY_NAME}.<br>
#                     <a href="#" style="color: {KRYSTO_PRIMARY};">Se désinscrire</a>
#                 </p>
#             </td>
#         </tr>
#     </table>
# </body>
# </html>'''


# def get_email_template_newsletter(title, intro, sections, cta_text="", cta_url=""):
#     """Template newsletter avec sections."""
#     sections_html = ""
#     for i, section in enumerate(sections):
#         icon = section.get('icon', '📌')
#         bg_color = "#f8f9fa" if i % 2 == 0 else "#ffffff"
#         sections_html += f'''
#         <tr>
#             <td style="padding: 25px 40px; background-color: {bg_color};">
#                 <table role="presentation" style="width: 100%;">
#                     <tr>
#                         <td style="width: 50px; vertical-align: top;">
#                             <div style="width: 45px; height: 45px; background: linear-gradient(135deg, {KRYSTO_PRIMARY}, {KRYSTO_SECONDARY}); 
#                                  border-radius: 12px; text-align: center; line-height: 45px; font-size: 22px;">{icon}</div>
#                         </td>
#                         <td style="padding-left: 15px;">
#                             <h3 style="margin: 0 0 8px 0; color: {KRYSTO_PRIMARY}; font-size: 17px;">{section.get('title', '')}</h3>
#                             <p style="margin: 0; color: {KRYSTO_DARK}; font-size: 14px; line-height: 1.7;">{section.get('content', '')}</p>
#                         </td>
#                     </tr>
#                 </table>
#             </td>
#         </tr>'''
    
#     cta_html = ""
#     if cta_text and cta_url:
#         cta_html = f'''
#         <tr>
#             <td align="center" style="padding: 30px 40px;">
#                 <a href="{cta_url}" style="display: inline-block; padding: 16px 45px; 
#                    background: linear-gradient(135deg, {KRYSTO_PRIMARY} 0%, {KRYSTO_SECONDARY} 100%); 
#                    color: #ffffff; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 15px;
#                    box-shadow: 0 4px 15px rgba(109, 116, 171, 0.4);">
#                    {cta_text} →
#                 </a>
#             </td>
#         </tr>'''
    
#     return f'''<!DOCTYPE html>
# <html lang="fr">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>{title}</title>
# </head>
# <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
#     <table role="presentation" style="width: 100%; border-collapse: collapse;">
#         <tr>
#             <td align="center" style="padding: 40px 0;">
#                 <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); overflow: hidden;">
                    
#                     <!-- Header Newsletter -->
#                     <tr>
#                         <td style="background: linear-gradient(135deg, {KRYSTO_PRIMARY} 0%, {KRYSTO_SECONDARY} 100%); padding: 40px; text-align: center;">
#                             <div style="font-size: 50px; margin-bottom: 15px;">♻️</div>
#                             <h1 style="margin: 0; color: #ffffff; font-size: 36px; font-weight: bold;">{COMPANY_NAME}</h1>
#                             <div style="margin-top: 15px; padding: 8px 25px; background: rgba(255,255,255,0.2); border-radius: 20px; display: inline-block;">
#                                 <span style="color: #ffffff; font-size: 12px; letter-spacing: 2px; text-transform: uppercase;">📰 Newsletter</span>
#                             </div>
#                         </td>
#                     </tr>
                    
#                     <!-- Titre -->
#                     <tr>
#                         <td style="padding: 35px 40px 20px 40px; text-align: center;">
#                             <h2 style="margin: 0; color: {KRYSTO_DARK}; font-size: 26px;">{title}</h2>
#                         </td>
#                     </tr>
                    
#                     <!-- Introduction -->
#                     <tr>
#                         <td style="padding: 0 40px 30px 40px; text-align: center;">
#                             <p style="margin: 0; color: #666666; font-size: 16px; line-height: 1.7;">{intro}</p>
#                         </td>
#                     </tr>
                    
#                     <!-- Séparateur décoratif -->
#                     <tr>
#                         <td style="padding: 0 40px;">
#                             <div style="height: 4px; background: linear-gradient(90deg, {KRYSTO_SECONDARY}, {KRYSTO_PRIMARY}, {KRYSTO_SECONDARY}); border-radius: 2px;"></div>
#                         </td>
#                     </tr>
                    
#                     <!-- Sections -->
#                     {sections_html}
                    
#                     {cta_html}
                    
#                     <!-- Footer -->
#                     <tr>
#                         <td style="padding: 30px 40px; background-color: {KRYSTO_DARK}; text-align: center;">
#                             <p style="margin: 0 0 10px 0; color: {KRYSTO_SECONDARY}; font-size: 16px; font-weight: bold;">{COMPANY_NAME}</p>
#                             <p style="margin: 0; color: #cccccc; font-size: 12px;">{COMPANY_ADDRESS} | {COMPANY_EMAIL}</p>
#                             <p style="margin: 15px 0 0 0; color: #888888; font-size: 10px;">
#                                 © {datetime.now().year} {COMPANY_NAME} - Tous droits réservés<br>
#                                 <a href="#" style="color: {KRYSTO_SECONDARY};">Se désinscrire</a>
#                             </p>
#                         </td>
#                     </tr>
#                 </table>
#             </td>
#         </tr>
#     </table>
# </body>
# </html>'''


# def get_email_template_promo(title, description, promo_code, expiry_date):
#     """Template promotion avec code promo."""
#     return f'''<!DOCTYPE html>
# <html lang="fr">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>{title}</title>
# </head>
# <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
#     <table role="presentation" style="width: 100%; border-collapse: collapse;">
#         <tr>
#             <td align="center" style="padding: 40px 0;">
#                 <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); overflow: hidden;">
                    
#                     <!-- Header Promo -->
#                     <tr>
#                         <td style="background: linear-gradient(135deg, {KRYSTO_SECONDARY} 0%, {KRYSTO_PRIMARY} 100%); padding: 45px 40px; text-align: center;">
#                             <div style="font-size: 70px; margin-bottom: 15px;">🎁</div>
#                             <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: bold; text-transform: uppercase;">{title}</h1>
#                         </td>
#                     </tr>
                    
#                     <!-- Contenu promo -->
#                     <tr>
#                         <td style="padding: 40px; text-align: center;">
#                             <p style="margin: 0 0 30px 0; color: {KRYSTO_DARK}; font-size: 18px; line-height: 1.7;">{description}</p>
                            
#                             <!-- Code promo -->
#                             <div style="background: linear-gradient(135deg, {KRYSTO_PRIMARY}, {KRYSTO_SECONDARY}); border-radius: 15px; padding: 25px; margin: 25px 0;">
#                                 <p style="margin: 0 0 10px 0; color: rgba(255,255,255,0.9); font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">Votre code promo</p>
#                                 <p style="margin: 0; color: #ffffff; font-size: 36px; font-weight: bold; letter-spacing: 5px;">{promo_code}</p>
#                             </div>
                            
#                             <p style="margin: 20px 0 0 0; color: #E63946; font-size: 14px; font-weight: bold;">
#                                 ⏰ Valable jusqu'au {expiry_date}
#                             </p>
#                         </td>
#                     </tr>
                    
#                     <!-- Bouton -->
#                     <tr>
#                         <td align="center" style="padding: 20px 40px 40px 40px;">
#                             <a href="https://{COMPANY_WEBSITE}" style="display: inline-block; padding: 18px 50px; 
#                                background: {KRYSTO_DARK}; color: {KRYSTO_SECONDARY}; text-decoration: none; 
#                                border-radius: 30px; font-weight: bold; font-size: 16px;">
#                                J'en profite →
#                             </a>
#                         </td>
#                     </tr>
                    
#                     <!-- Footer -->
#                     <tr>
#                         <td style="padding: 25px 40px; background-color: {KRYSTO_DARK}; text-align: center;">
#                             <p style="margin: 0; color: #888888; font-size: 11px;">
#                                 {COMPANY_NAME} • {COMPANY_ADDRESS}<br>
#                                 © {datetime.now().year} - <a href="#" style="color: {KRYSTO_SECONDARY};">Se désinscrire</a>
#                             </p>
#                         </td>
#                     </tr>
#                 </table>
#             </td>
#         </tr>
#     </table>
# </body>
# </html>'''


# # Garder l'ancien template pour compatibilité
# def get_email_template(subject, content, footer_text=""):
#     return get_email_template_simple(subject, content, True)

# def get_newsletter_template(title, intro, sections, cta_text="", cta_url=""):
#     # Convertir l'ancien format
#     new_sections = []
#     for s in sections:
#         new_sections.append({
#             'icon': '📌',
#             'title': s.get('title', ''),
#             'content': s.get('content', '')
#         })
#     return get_email_template_newsletter(title, intro, new_sections, cta_text, cta_url)


# # ============================================================================
# # SERVICE EMAIL AMÉLIORÉ
# # ============================================================================
# class EmailService:
#     """Service d'envoi d'emails avec config dynamique."""
    
#     def __init__(self, config=None):
#         self.config = config or load_smtp_config()
    
#     def update_config(self, config):
#         self.config = config
    
#     def test_connection(self) -> tuple:
#         """Teste la connexion SMTP."""
#         try:
#             if self.config.get('use_ssl', True):
#                 context = ssl.create_default_context()
#                 with smtplib.SMTP_SSL(self.config['host'], self.config['port'], 
#                                        context=context, timeout=15) as server:
#                     server.login(self.config['username'], self.config['password'])
#                     return True, "✅ Connexion SMTP réussie!"
#             else:
#                 with smtplib.SMTP(self.config['host'], self.config['port'], timeout=15) as server:
#                     server.starttls()
#                     server.login(self.config['username'], self.config['password'])
#                     return True, "✅ Connexion SMTP réussie!"
#         except smtplib.SMTPAuthenticationError as e:
#             return False, f"❌ Authentification échouée!\n\nVérifiez:\n• Email: {self.config['username']}\n• Mot de passe\n\nErreur: {e}"
#         except smtplib.SMTPConnectError as e:
#             return False, f"❌ Impossible de se connecter au serveur\n{self.config['host']}:{self.config['port']}\n\nErreur: {e}"
#         except TimeoutError:
#             return False, f"❌ Timeout - Le serveur {self.config['host']} ne répond pas"
#         except Exception as e:
#             return False, f"❌ Erreur: {type(e).__name__}\n{str(e)}"
    
#     def send_email(self, to_email: str, subject: str, html_content: str, plain_text: str = "") -> tuple:
#         """Envoie un email HTML."""
#         try:
#             msg = MIMEMultipart('alternative')
#             msg['Subject'] = subject
#             msg['From'] = f"{self.config.get('from_name', COMPANY_NAME)} <{self.config['username']}>"
#             msg['To'] = to_email
            
#             if not plain_text:
#                 plain_text = f"{subject}\n\nCet email est au format HTML."
            
#             msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
#             msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
#             if self.config.get('use_ssl', True):
#                 context = ssl.create_default_context()
#                 with smtplib.SMTP_SSL(self.config['host'], self.config['port'], 
#                                        context=context, timeout=30) as server:
#                     server.login(self.config['username'], self.config['password'])
#                     server.sendmail(self.config['username'], to_email, msg.as_string())
#             else:
#                 with smtplib.SMTP(self.config['host'], self.config['port'], timeout=30) as server:
#                     server.starttls()
#                     server.login(self.config['username'], self.config['password'])
#                     server.sendmail(self.config['username'], to_email, msg.as_string())
            
#             return True, "Email envoyé avec succès"
#         except smtplib.SMTPAuthenticationError:
#             return False, "Authentification échouée - Vérifiez le mot de passe"
#         except smtplib.SMTPRecipientsRefused:
#             return False, f"Adresse refusée: {to_email}"
#         except Exception as e:
#             return False, str(e)
    
#     def send_bulk_emails(self, recipients: list, subject: str, html_content: str, callback=None) -> dict:
#         """Envoie des emails en masse avec personnalisation."""
#         import time
#         results = {'success': 0, 'failed': 0, 'errors': []}
        
#         for i, recipient in enumerate(recipients):
#             email = recipient.get('email')
#             name = recipient.get('name', '')
            
#             if not email or '@' not in email:
#                 results['failed'] += 1
#                 results['errors'].append(f"Email invalide: {name}")
#                 continue
            
#             # Personnaliser le contenu
#             personalized_html = html_content.replace('{{name}}', name)
#             personalized_html = personalized_html.replace('{{email}}', email)
#             personalized_html = personalized_html.replace('{{date}}', datetime.now().strftime('%d/%m/%Y'))
            
#             success, msg = self.send_email(email, subject, personalized_html)
            
#             if success:
#                 results['success'] += 1
#             else:
#                 results['failed'] += 1
#                 results['errors'].append(f"{email}: {msg}")
            
#             if callback:
#                 callback(i + 1, len(recipients), email, success)
            
#             # Délai anti-spam
#             time.sleep(0.5)
        
#         return results




# # ============================================================================
# # BASE DE DONNÉES (code original complet)
# # ============================================================================
# class DatabaseManager:
#     def __init__(self):
#         self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
#         self.conn.row_factory = sqlite3.Row
#         self.conn.execute("PRAGMA foreign_keys = ON")
#         self.create_tables()
    
#     def create_tables(self):
#         c = self.conn.cursor()
        
#         c.execute('''CREATE TABLE IF NOT EXISTS colors (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT UNIQUE NOT NULL,
#             hex_code TEXT DEFAULT '#808080',
#             plastic_type TEXT,
#             stock_kg REAL DEFAULT 0,
#             price_per_kg REAL DEFAULT 0,
#             supplier TEXT,
#             alert_threshold REAL DEFAULT 2.0,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS categories (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT UNIQUE NOT NULL,
#             color TEXT DEFAULT '#6d74ab'
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS recipes (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             description TEXT,
#             plastic_type TEXT,
#             image_path TEXT,
#             category_id INTEGER,
#             production_count INTEGER DEFAULT 0,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (category_id) REFERENCES categories(id)
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS recipe_ingredients (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             recipe_id INTEGER NOT NULL,
#             color_id INTEGER NOT NULL,
#             percentage REAL NOT NULL,
#             FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
#             FOREIGN KEY (color_id) REFERENCES colors(id)
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS machines (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             machine_type TEXT NOT NULL,
#             brand TEXT, model TEXT, serial_number TEXT,
#             voltage TEXT DEFAULT '220V',
#             power_watts INTEGER, max_temp INTEGER,
#             shot_size_g REAL, shot_size_cm3 REAL,
#             output_rate TEXT, dimensions TEXT,
#             compatible_plastics TEXT,
#             purchase_date DATE, purchase_price REAL, notes TEXT,
#             total_hours REAL DEFAULT 0,
#             status TEXT DEFAULT 'active',
#             last_maintenance DATE,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS molds (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             reference TEXT, dimensions TEXT,
#             material TEXT DEFAULT 'Aluminium',
#             compatible_plastics TEXT, compatible_machines TEXT,
#             shot_volume_g REAL, part_weight_g REAL,
#             items_per_shot INTEGER DEFAULT 1,
#             qty_per_hour INTEGER, cycle_time_sec INTEGER,
#             price_xpf REAL DEFAULT 0,
#             purchase_date DATE, notes TEXT,
#             usage_count INTEGER DEFAULT 0,
#             status TEXT DEFAULT 'active',
#             last_maintenance DATE,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS maintenance_log (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             machine_id INTEGER, mold_id INTEGER,
#             maintenance_type TEXT, description TEXT,
#             parts_replaced TEXT, cost REAL DEFAULT 0,
#             technician TEXT,
#             maintenance_date DATE DEFAULT CURRENT_DATE,
#             next_maintenance DATE,
#             FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE,
#             FOREIGN KEY (mold_id) REFERENCES molds(id) ON DELETE CASCADE
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS production_log (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             recipe_id INTEGER, recipe_name TEXT,
#             quantity_kg REAL NOT NULL,
#             machine_id INTEGER, mold_id INTEGER,
#             quality_rating INTEGER, notes TEXT,
#             production_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS production_consumption (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             production_id INTEGER NOT NULL,
#             color_id INTEGER NOT NULL,
#             quantity_kg REAL NOT NULL,
#             FOREIGN KEY (production_id) REFERENCES production_log(id) ON DELETE CASCADE
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS stock_movements (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             color_id INTEGER NOT NULL,
#             quantity_kg REAL NOT NULL,
#             movement_type TEXT NOT NULL,
#             reason TEXT,
#             movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (color_id) REFERENCES colors(id)
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS filament_production (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             color_id INTEGER, color_name TEXT,
#             weight_g REAL, length_m REAL,
#             production_time_h REAL, extrusion_temp INTEGER,
#             quality_rating INTEGER, batch_number TEXT,
#             machine_id INTEGER, notes TEXT,
#             production_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (color_id) REFERENCES colors(id)
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS filament_spools (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             production_id INTEGER, color_name TEXT,
#             weight_g REAL, remaining_g REAL,
#             quality_rating INTEGER, batch_number TEXT,
#             status TEXT DEFAULT 'available',
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS products (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             reference TEXT UNIQUE,
#             description TEXT,
#             recipe_id INTEGER, mold_id INTEGER,
#             weight_g REAL, production_cost REAL,
#             sell_price REAL DEFAULT 0, category TEXT,
#             stock_qty INTEGER DEFAULT 0, min_stock INTEGER DEFAULT 5,
#             image_path TEXT,
#             FOREIGN KEY (recipe_id) REFERENCES recipes(id),
#             FOREIGN KEY (mold_id) REFERENCES molds(id)
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS clients (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             company TEXT,
#             is_professional INTEGER DEFAULT 0,
#             ridet TEXT,
#             email TEXT, phone TEXT,
#             address TEXT, city TEXT, notes TEXT,
#             newsletter_subscribed INTEGER DEFAULT 1,
#             total_purchases REAL DEFAULT 0,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS sales (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             client_id INTEGER, product_id INTEGER NOT NULL,
#             quantity INTEGER NOT NULL,
#             unit_price REAL, total_price REAL,
#             sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (client_id) REFERENCES clients(id),
#             FOREIGN KEY (product_id) REFERENCES products(id)
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS orders (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             order_number TEXT UNIQUE NOT NULL,
#             client_id INTEGER,
#             status TEXT DEFAULT 'pending',
#             priority TEXT DEFAULT 'normal',
#             order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             due_date DATE, delivery_date DATE,
#             notes TEXT, total_amount REAL DEFAULT 0,
#             FOREIGN KEY (client_id) REFERENCES clients(id)
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS order_items (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             order_id INTEGER NOT NULL,
#             product_id INTEGER, product_name TEXT,
#             quantity INTEGER NOT NULL,
#             unit_price REAL, notes TEXT,
#             FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
#             FOREIGN KEY (product_id) REFERENCES products(id)
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS production_orders (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             of_number TEXT UNIQUE NOT NULL,
#             order_id INTEGER, product_id INTEGER,
#             recipe_id INTEGER, mold_id INTEGER, machine_id INTEGER,
#             quantity INTEGER NOT NULL,
#             quantity_produced INTEGER DEFAULT 0,
#             status TEXT DEFAULT 'draft',
#             priority TEXT DEFAULT 'normal',
#             planned_date DATE,
#             start_date TIMESTAMP, end_date TIMESTAMP,
#             operator TEXT, notes TEXT,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (order_id) REFERENCES orders(id),
#             FOREIGN KEY (product_id) REFERENCES products(id),
#             FOREIGN KEY (recipe_id) REFERENCES recipes(id),
#             FOREIGN KEY (mold_id) REFERENCES molds(id),
#             FOREIGN KEY (machine_id) REFERENCES machines(id)
#         )''')
        
#         c.execute('''CREATE TABLE IF NOT EXISTS email_history (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             subject TEXT, recipient_type TEXT,
#             recipients_count INTEGER,
#             success_count INTEGER, failed_count INTEGER,
#             sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )''')
        
#         self._insert_defaults(c)
#         self._migrate(c)
#         self.conn.commit()
    
#     def _migrate(self, c):
#         for col in ["is_professional", "ridet", "newsletter_subscribed"]:
#             try: c.execute(f"ALTER TABLE clients ADD COLUMN {col} {'INTEGER DEFAULT 0' if col != 'ridet' else 'TEXT'}")
#             except: pass
    
#     def _insert_defaults(self, c):
#         c.execute("SELECT COUNT(*) FROM colors")
#         if c.fetchone()[0] == 0:
#             colors = [("Blanc", "#FFFFFF", "HDPE", 10.0, 300), ("Noir", "#1a1a1a", "HDPE", 8.0, 250),
#                 ("Gris", "#808080", "HDPE", 5.0, 280), ("Rouge", "#E63946", "HDPE", 3.0, 350),
#                 ("Bleu KRYSTO", KRYSTO_PRIMARY, "HDPE", 4.0, 330), ("Turquoise KRYSTO", KRYSTO_SECONDARY, "HDPE", 3.5, 330),
#                 ("Jaune", "#FFD60A", "HDPE", 2.0, 350), ("Orange", "#F77F00", "PP", 2.5, 350)]
#             c.executemany("INSERT INTO colors (name, hex_code, plastic_type, stock_kg, price_per_kg) VALUES (?, ?, ?, ?, ?)", colors)
        
#         c.execute("SELECT COUNT(*) FROM categories")
#         if c.fetchone()[0] == 0:
#             c.executemany("INSERT INTO categories (name, color) VALUES (?, ?)", 
#                 [("Clients", KRYSTO_PRIMARY), ("Tests", "#F77F00"), ("Best-sellers", KRYSTO_SECONDARY)])
        
#         c.execute("SELECT COUNT(*) FROM machines")
#         if c.fetchone()[0] == 0:
#             c.executemany("INSERT INTO machines (name, machine_type, brand, model, voltage, max_temp) VALUES (?, ?, ?, ?, ?, ?)",
#                 [("Injection Mini V2", "injecteuse", "Precious Plastic", "Mini V2", "220V", 280),
#                  ("Arbour Injection", "injecteuse", "Precious Plastic", "Arbour", "220V", 300),
#                  ("Broyeur", "broyeur", "Precious Plastic", "Shredder", "220V", None)])

#     # === COULEURS ===
#     def get_all_colors(self): return self.conn.execute("SELECT * FROM colors ORDER BY name").fetchall()
#     def get_low_stock_colors(self): return self.conn.execute("SELECT * FROM colors WHERE stock_kg <= alert_threshold").fetchall()
#     def add_color(self, name, hex_code, plastic_type, stock=0, price=0, alert=2.0, supplier=""):
#         try:
#             self.conn.execute("INSERT INTO colors (name, hex_code, plastic_type, stock_kg, price_per_kg, alert_threshold, supplier) VALUES (?, ?, ?, ?, ?, ?, ?)",
#                 (name, hex_code, plastic_type, stock, price, alert, supplier))
#             self.conn.commit(); return True
#         except: return False
#     def add_stock_movement(self, color_id, qty, mov_type, reason=""):
#         self.conn.execute("INSERT INTO stock_movements (color_id, quantity_kg, movement_type, reason) VALUES (?, ?, ?, ?)", (color_id, qty, mov_type, reason))
#         op = "+" if mov_type == "entree" else "-"
#         self.conn.execute(f"UPDATE colors SET stock_kg = stock_kg {op} ? WHERE id = ?", (qty, color_id))
#         self.conn.commit()
#     def delete_color(self, color_id): self.conn.execute("DELETE FROM colors WHERE id = ?", (color_id,)); self.conn.commit()

#     # === CATÉGORIES ===
#     def get_all_categories(self): return self.conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
#     def add_category(self, name, color=KRYSTO_PRIMARY):
#         try: self.conn.execute("INSERT INTO categories (name, color) VALUES (?, ?)", (name, color)); self.conn.commit(); return True
#         except: return False

#     # === RECETTES ===
#     def get_all_recipes(self, search="", plastic_type="", category_id=None):
#         q = "SELECT r.*, c.name as category_name, c.color as category_color FROM recipes r LEFT JOIN categories c ON r.category_id = c.id WHERE 1=1"
#         p = []
#         if search: q += " AND (r.name LIKE ? OR r.description LIKE ?)"; p.extend([f"%{search}%"]*2)
#         if plastic_type: q += " AND r.plastic_type = ?"; p.append(plastic_type)
#         if category_id: q += " AND r.category_id = ?"; p.append(category_id)
#         return self.conn.execute(q + " ORDER BY r.created_at DESC", p).fetchall()
    
#     def get_recipe(self, rid): return self.conn.execute("SELECT r.*, c.name as category_name FROM recipes r LEFT JOIN categories c ON r.category_id = c.id WHERE r.id = ?", (rid,)).fetchone()
#     def get_recipe_ingredients(self, rid):
#         return self.conn.execute('''SELECT ri.*, c.name as color_name, c.hex_code, c.stock_kg, c.price_per_kg
#             FROM recipe_ingredients ri JOIN colors c ON ri.color_id = c.id WHERE ri.recipe_id = ? ORDER BY ri.percentage DESC''', (rid,)).fetchall()
#     def get_recipe_cost(self, rid): return sum((i['percentage']/100) * (i['price_per_kg'] or 0) for i in self.get_recipe_ingredients(rid))
    
#     def save_recipe(self, name, desc, plastic_type, ingredients, image_path=None, category_id=None, recipe_id=None):
#         c = self.conn.cursor()
#         if recipe_id:
#             c.execute("UPDATE recipes SET name=?, description=?, plastic_type=?, image_path=?, category_id=? WHERE id=?", (name, desc, plastic_type, image_path, category_id, recipe_id))
#             c.execute("DELETE FROM recipe_ingredients WHERE recipe_id=?", (recipe_id,))
#         else:
#             c.execute("INSERT INTO recipes (name, description, plastic_type, image_path, category_id) VALUES (?, ?, ?, ?, ?)", (name, desc, plastic_type, image_path, category_id))
#             recipe_id = c.lastrowid
#         for color_id, pct in ingredients:
#             c.execute("INSERT INTO recipe_ingredients (recipe_id, color_id, percentage) VALUES (?, ?, ?)", (recipe_id, color_id, pct))
#         self.conn.commit(); return recipe_id
    
#     def duplicate_recipe(self, rid):
#         r = self.get_recipe(rid); ings = self.get_recipe_ingredients(rid)
#         return self.save_recipe(f"{r['name']} (copie)", r['description'], r['plastic_type'], [(i['color_id'], i['percentage']) for i in ings], r['image_path'], r['category_id'])
#     def delete_recipe(self, rid): self.conn.execute("DELETE FROM recipes WHERE id = ?", (rid,)); self.conn.commit()

#     # === MACHINES ===
#     def get_all_machines(self, mtype=None):
#         if mtype: return self.conn.execute("SELECT * FROM machines WHERE machine_type = ? ORDER BY name", (mtype,)).fetchall()
#         return self.conn.execute("SELECT * FROM machines ORDER BY machine_type, name").fetchall()
#     def get_machine(self, mid): return self.conn.execute("SELECT * FROM machines WHERE id = ?", (mid,)).fetchone()
#     def save_machine(self, name, mtype, brand="", model="", serial="", voltage="220V", power=None, max_temp=None, shot_g=None, shot_cm3=None, output_rate="", dimensions="", plastics="", notes="", purchase_date=None, purchase_price=None, machine_id=None):
#         if machine_id:
#             self.conn.execute("UPDATE machines SET name=?, machine_type=?, brand=?, model=?, serial_number=?, voltage=?, power_watts=?, max_temp=?, shot_size_g=?, shot_size_cm3=?, output_rate=?, dimensions=?, compatible_plastics=?, notes=?, purchase_date=?, purchase_price=? WHERE id=?",
#                 (name, mtype, brand, model, serial, voltage, power, max_temp, shot_g, shot_cm3, output_rate, dimensions, plastics, notes, purchase_date, purchase_price, machine_id))
#         else:
#             self.conn.execute("INSERT INTO machines (name, machine_type, brand, model, serial_number, voltage, power_watts, max_temp, shot_size_g, shot_size_cm3, output_rate, dimensions, compatible_plastics, notes, purchase_date, purchase_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#                 (name, mtype, brand, model, serial, voltage, power, max_temp, shot_g, shot_cm3, output_rate, dimensions, plastics, notes, purchase_date, purchase_price))
#         self.conn.commit()
#     def delete_machine(self, mid): self.conn.execute("DELETE FROM machines WHERE id = ?", (mid,)); self.conn.commit()

#     # === MOULES ===
#     def get_all_molds(self): return self.conn.execute("SELECT * FROM molds ORDER BY name").fetchall()
#     def get_mold(self, mid): return self.conn.execute("SELECT * FROM molds WHERE id = ?", (mid,)).fetchone()
#     def save_mold(self, name, reference="", dimensions="", material="Aluminium", plastics="", machines="", shot_g=None, part_g=None, items=1, qty_hour=None, cycle_sec=None, price=0, notes="", purchase_date=None, mold_id=None):
#         if mold_id:
#             self.conn.execute("UPDATE molds SET name=?, reference=?, dimensions=?, material=?, compatible_plastics=?, compatible_machines=?, shot_volume_g=?, part_weight_g=?, items_per_shot=?, qty_per_hour=?, cycle_time_sec=?, price_xpf=?, notes=?, purchase_date=? WHERE id=?",
#                 (name, reference, dimensions, material, plastics, machines, shot_g, part_g, items, qty_hour, cycle_sec, price, notes, purchase_date, mold_id))
#         else:
#             self.conn.execute("INSERT INTO molds (name, reference, dimensions, material, compatible_plastics, compatible_machines, shot_volume_g, part_weight_g, items_per_shot, qty_per_hour, cycle_time_sec, price_xpf, notes, purchase_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#                 (name, reference, dimensions, material, plastics, machines, shot_g, part_g, items, qty_hour, cycle_sec, price, notes, purchase_date))
#         self.conn.commit()
#     def delete_mold(self, mid): self.conn.execute("DELETE FROM molds WHERE id = ?", (mid,)); self.conn.commit()

#     # === MAINTENANCE ===
#     def add_maintenance(self, machine_id=None, mold_id=None, mtype="", desc="", parts="", cost=0, tech="", next_date=None):
#         self.conn.execute("INSERT INTO maintenance_log (machine_id, mold_id, maintenance_type, description, parts_replaced, cost, technician, next_maintenance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
#             (machine_id, mold_id, mtype, desc, parts, cost, tech, next_date))
#         if machine_id: self.conn.execute("UPDATE machines SET last_maintenance = DATE('now') WHERE id = ?", (machine_id,))
#         if mold_id: self.conn.execute("UPDATE molds SET last_maintenance = DATE('now') WHERE id = ?", (mold_id,))
#         self.conn.commit()
#     def get_machine_maintenance(self, mid): return self.conn.execute("SELECT * FROM maintenance_log WHERE machine_id = ? ORDER BY maintenance_date DESC LIMIT 20", (mid,)).fetchall()
#     def get_mold_maintenance(self, mid): return self.conn.execute("SELECT * FROM maintenance_log WHERE mold_id = ? ORDER BY maintenance_date DESC LIMIT 20", (mid,)).fetchall()
#     def get_all_maintenance(self, limit=50):
#         return self.conn.execute("SELECT ml.*, m.name as machine_name, mo.name as mold_name FROM maintenance_log ml LEFT JOIN machines m ON ml.machine_id = m.id LEFT JOIN molds mo ON ml.mold_id = mo.id ORDER BY ml.maintenance_date DESC LIMIT ?", (limit,)).fetchall()

#     # === PRODUCTION ===
#     def log_production(self, recipe_id, recipe_name, qty_kg, consumption, machine_id=None, mold_id=None, quality=None, notes=""):
#         c = self.conn.cursor()
#         c.execute("INSERT INTO production_log (recipe_id, recipe_name, quantity_kg, machine_id, mold_id, quality_rating, notes) VALUES (?, ?, ?, ?, ?, ?, ?)", (recipe_id, recipe_name, qty_kg, machine_id, mold_id, quality, notes))
#         prod_id = c.lastrowid
#         for color_id, qty in consumption:
#             c.execute("INSERT INTO production_consumption (production_id, color_id, quantity_kg) VALUES (?, ?, ?)", (prod_id, color_id, qty))
#             c.execute("UPDATE colors SET stock_kg = stock_kg - ? WHERE id = ?", (qty, color_id))
#         if recipe_id: c.execute("UPDATE recipes SET production_count = production_count + 1 WHERE id = ?", (recipe_id,))
#         if mold_id: c.execute("UPDATE molds SET usage_count = usage_count + 1 WHERE id = ?", (mold_id,))
#         self.conn.commit(); return prod_id
    
#     def get_production_stats(self, days=30):
#         start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
#         return {
#             'total': self.conn.execute("SELECT COALESCE(SUM(quantity_kg), 0) FROM production_log").fetchone()[0],
#             'period': self.conn.execute("SELECT COALESCE(SUM(quantity_kg), 0) FROM production_log WHERE production_date >= ?", (start,)).fetchone()[0]
#         }

#     # === FILAMENT ===
#     def log_filament(self, color_id, color_name, weight_g, temp=None, quality=None, machine_id=None, notes=""):
#         length = calc_filament_length(weight_g); time_info = calc_production_time(weight_g); batch = f"FIL-{datetime.now().strftime('%Y%m%d%H%M')}"
#         c = self.conn.cursor()
#         c.execute("INSERT INTO filament_production (color_id, color_name, weight_g, length_m, production_time_h, extrusion_temp, quality_rating, batch_number, machine_id, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#             (color_id, color_name, weight_g, length, time_info['hours'], temp, quality, batch, machine_id, notes))
#         prod_id = c.lastrowid
#         c.execute("INSERT INTO filament_spools (production_id, color_name, weight_g, remaining_g, quality_rating, batch_number) VALUES (?, ?, ?, ?, ?, ?)", (prod_id, color_name, weight_g, weight_g, quality, batch))
#         if color_id: c.execute("UPDATE colors SET stock_kg = stock_kg - ? WHERE id = ?", (weight_g / 1000, color_id))
#         self.conn.commit(); return prod_id
#     def get_filament_history(self, limit=50): return self.conn.execute("SELECT * FROM filament_production ORDER BY production_date DESC LIMIT ?", (limit,)).fetchall()
#     def get_filament_stats(self):
#         r = self.conn.execute("SELECT COALESCE(SUM(weight_g), 0), COALESCE(SUM(length_m), 0), COALESCE(SUM(production_time_h), 0) FROM filament_production").fetchone()
#         return {'total_g': r[0], 'total_length': r[1], 'total_hours': r[2],
#             'avg_quality': self.conn.execute("SELECT AVG(quality_rating) FROM filament_production WHERE quality_rating IS NOT NULL").fetchone()[0] or 0,
#             'spools': self.conn.execute("SELECT COUNT(*) FROM filament_spools WHERE status = 'available'").fetchone()[0],
#             'month_g': self.conn.execute("SELECT COALESCE(SUM(weight_g), 0) FROM filament_production WHERE production_date >= date('now', 'start of month')").fetchone()[0]}

#     # === PRODUITS ===
#     def get_all_products(self, search=""):
#         q = "SELECT p.*, r.name as recipe_name, m.name as mold_name FROM products p LEFT JOIN recipes r ON p.recipe_id = r.id LEFT JOIN molds m ON p.mold_id = m.id"
#         if search: q += f" WHERE p.name LIKE '%{search}%' OR p.reference LIKE '%{search}%'"
#         return self.conn.execute(q + " ORDER BY p.name").fetchall()
#     def get_product(self, pid): return self.conn.execute("SELECT p.*, r.name as recipe_name, m.name as mold_name FROM products p LEFT JOIN recipes r ON p.recipe_id = r.id LEFT JOIN molds m ON p.mold_id = m.id WHERE p.id = ?", (pid,)).fetchone()
#     def get_low_stock_products(self): return self.conn.execute("SELECT * FROM products WHERE stock_qty <= min_stock").fetchall()
#     def save_product(self, name, reference, description, recipe_id, mold_id, weight_g, sell_price, category, min_stock, image_path=None, product_id=None):
#         cost = self.get_recipe_cost(recipe_id) * (weight_g / 1000) if recipe_id else 0
#         if product_id:
#             self.conn.execute("UPDATE products SET name=?, reference=?, description=?, recipe_id=?, mold_id=?, weight_g=?, production_cost=?, sell_price=?, category=?, min_stock=?, image_path=? WHERE id=?",
#                 (name, reference, description, recipe_id, mold_id, weight_g, cost, sell_price, category, min_stock, image_path, product_id))
#         else:
#             self.conn.execute("INSERT INTO products (name, reference, description, recipe_id, mold_id, weight_g, production_cost, sell_price, category, min_stock, image_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#                 (name, reference, description, recipe_id, mold_id, weight_g, cost, sell_price, category, min_stock, image_path))
#         self.conn.commit()
#     def add_product_stock(self, pid, qty): self.conn.execute("UPDATE products SET stock_qty = stock_qty + ? WHERE id = ?", (qty, pid)); self.conn.commit()
#     def delete_product(self, pid): self.conn.execute("DELETE FROM products WHERE id = ?", (pid,)); self.conn.commit()

#     # === CLIENTS ===
#     def get_all_clients(self, search="", client_type=None):
#         q = "SELECT * FROM clients WHERE 1=1"; p = []
#         if search: q += " AND (name LIKE ? OR company LIKE ? OR email LIKE ?)"; p.extend([f"%{search}%"]*3)
#         if client_type == "pro": q += " AND is_professional = 1"
#         elif client_type == "particulier": q += " AND is_professional = 0"
#         return self.conn.execute(q + " ORDER BY name", p).fetchall()
#     def get_clients_for_mailing(self, client_type=None, subscribed_only=True):
#         q = "SELECT * FROM clients WHERE email IS NOT NULL AND email != ''"
#         if subscribed_only: q += " AND newsletter_subscribed = 1"
#         if client_type == "pro": q += " AND is_professional = 1"
#         elif client_type == "particulier": q += " AND is_professional = 0"
#         return self.conn.execute(q).fetchall()
#     def get_client(self, cid): return self.conn.execute("SELECT * FROM clients WHERE id = ?", (cid,)).fetchone()
#     def save_client(self, name, company="", is_professional=0, ridet="", email="", phone="", address="", city="", notes="", newsletter=1, client_id=None):
#         if client_id:
#             self.conn.execute("UPDATE clients SET name=?, company=?, is_professional=?, ridet=?, email=?, phone=?, address=?, city=?, notes=?, newsletter_subscribed=? WHERE id=?",
#                 (name, company, is_professional, ridet, email, phone, address, city, notes, newsletter, client_id))
#         else:
#             self.conn.execute("INSERT INTO clients (name, company, is_professional, ridet, email, phone, address, city, notes, newsletter_subscribed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#                 (name, company, is_professional, ridet, email, phone, address, city, notes, newsletter))
#         self.conn.commit()
#     def delete_client(self, cid): self.conn.execute("DELETE FROM clients WHERE id = ?", (cid,)); self.conn.commit()
#     def get_client_stats(self):
#         total = self.conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
#         pro = self.conn.execute("SELECT COUNT(*) FROM clients WHERE is_professional = 1").fetchone()[0]
#         with_email = self.conn.execute("SELECT COUNT(*) FROM clients WHERE email IS NOT NULL AND email != ''").fetchone()[0]
#         subscribed = self.conn.execute("SELECT COUNT(*) FROM clients WHERE newsletter_subscribed = 1 AND email IS NOT NULL AND email != ''").fetchone()[0]
#         return {'total': total, 'pro': pro, 'particulier': total - pro, 'with_email': with_email, 'subscribed': subscribed}

#     # === COMMANDES ===
#     def get_all_orders(self, status=None):
#         q = "SELECT o.*, c.name as client_name, c.company as client_company, c.is_professional FROM orders o LEFT JOIN clients c ON o.client_id = c.id"
#         if status: q += f" WHERE o.status = '{status}'"
#         return self.conn.execute(q + " ORDER BY o.order_date DESC").fetchall()
#     def get_order(self, oid): return self.conn.execute("SELECT o.*, c.name as client_name, c.company, c.email, c.phone, c.address, c.city, c.is_professional, c.ridet FROM orders o LEFT JOIN clients c ON o.client_id = c.id WHERE o.id = ?", (oid,)).fetchone()
#     def get_order_items(self, oid): return self.conn.execute("SELECT oi.*, p.reference FROM order_items oi LEFT JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?", (oid,)).fetchall()
#     def create_order(self, client_id, items, priority="normal", due_date=None, notes=""):
#         num = generate_order_number(); c = self.conn.cursor()
#         c.execute("INSERT INTO orders (order_number, client_id, priority, due_date, notes) VALUES (?, ?, ?, ?, ?)", (num, client_id, priority, due_date, notes))
#         oid = c.lastrowid; total = 0
#         for item in items:
#             c.execute("INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, notes) VALUES (?, ?, ?, ?, ?, ?)",
#                 (oid, item.get('product_id'), item.get('product_name'), item['quantity'], item.get('unit_price', 0), item.get('notes', '')))
#             total += item['quantity'] * item.get('unit_price', 0)
#         c.execute("UPDATE orders SET total_amount = ? WHERE id = ?", (total, oid))
#         self.conn.commit(); return oid, num
#     def update_order_status(self, oid, status):
#         self.conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, oid))
#         if status == 'delivered': self.conn.execute("UPDATE orders SET delivery_date = DATE('now') WHERE id = ?", (oid,))
#         self.conn.commit()
#     def delete_order(self, oid): self.conn.execute("DELETE FROM orders WHERE id = ?", (oid,)); self.conn.commit()

#     # === OF ===
#     def get_all_of(self, status=None):
#         q = """SELECT po.*, p.name as product_name, p.reference as product_ref, r.name as recipe_name,
#             m.name as mold_name, ma.name as machine_name, o.order_number, c.name as client_name
#             FROM production_orders po LEFT JOIN products p ON po.product_id = p.id
#             LEFT JOIN recipes r ON po.recipe_id = r.id LEFT JOIN molds m ON po.mold_id = m.id
#             LEFT JOIN machines ma ON po.machine_id = ma.id LEFT JOIN orders o ON po.order_id = o.id
#             LEFT JOIN clients c ON o.client_id = c.id"""
#         if status: q += f" WHERE po.status = '{status}'"
#         return self.conn.execute(q + " ORDER BY po.created_at DESC").fetchall()
#     def get_of(self, oid):
#         return self.conn.execute("""SELECT po.*, p.name as product_name, p.reference as product_ref, p.weight_g,
#             r.name as recipe_name, r.plastic_type, m.name as mold_name, m.items_per_shot, m.cycle_time_sec,
#             ma.name as machine_name, o.order_number, c.name as client_name, c.company as client_company
#             FROM production_orders po LEFT JOIN products p ON po.product_id = p.id
#             LEFT JOIN recipes r ON po.recipe_id = r.id LEFT JOIN molds m ON po.mold_id = m.id
#             LEFT JOIN machines ma ON po.machine_id = ma.id LEFT JOIN orders o ON po.order_id = o.id
#             LEFT JOIN clients c ON o.client_id = c.id WHERE po.id = ?""", (oid,)).fetchone()
#     def create_of(self, product_id, recipe_id, mold_id, machine_id, qty, order_id=None, priority="normal", planned_date=None, operator="", notes=""):
#         num = generate_of_number()
#         self.conn.execute("INSERT INTO production_orders (of_number, order_id, product_id, recipe_id, mold_id, machine_id, quantity, priority, planned_date, operator, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#             (num, order_id, product_id, recipe_id, mold_id, machine_id, qty, priority, planned_date, operator, notes))
#         self.conn.commit(); return num
#     def update_of_status(self, oid, status, qty_produced=None):
#         if status == 'in_progress':
#             self.conn.execute("UPDATE production_orders SET status = ?, start_date = CURRENT_TIMESTAMP WHERE id = ?", (status, oid))
#         elif status == 'completed':
#             self.conn.execute("UPDATE production_orders SET status = ?, end_date = CURRENT_TIMESTAMP, quantity_produced = ? WHERE id = ?", (status, qty_produced, oid))
#             of = self.get_of(oid)
#             if of and of['product_id']: self.add_product_stock(of['product_id'], qty_produced or of['quantity'])
#         else:
#             self.conn.execute("UPDATE production_orders SET status = ? WHERE id = ?", (status, oid))
#         self.conn.commit()
#     def delete_of(self, oid): self.conn.execute("DELETE FROM production_orders WHERE id = ?", (oid,)); self.conn.commit()

#     # === EMAIL HISTORY ===
#     def log_email_campaign(self, subject, rtype, count, success, failed):
#         self.conn.execute("INSERT INTO email_history (subject, recipient_type, recipients_count, success_count, failed_count) VALUES (?, ?, ?, ?, ?)", (subject, rtype, count, success, failed))
#         self.conn.commit()
#     def get_email_history(self, limit=20): return self.conn.execute("SELECT * FROM email_history ORDER BY sent_at DESC LIMIT ?", (limit,)).fetchall()

#     # === VENTES ===
#     def add_sale(self, product_id, quantity, unit_price, client_id=None):
#         total = quantity * unit_price
#         self.conn.execute("INSERT INTO sales (client_id, product_id, quantity, unit_price, total_price) VALUES (?, ?, ?, ?, ?)", (client_id, product_id, quantity, unit_price, total))
#         self.conn.execute("UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?", (quantity, product_id))
#         if client_id: self.conn.execute("UPDATE clients SET total_purchases = total_purchases + ? WHERE id = ?", (total, client_id))
#         self.conn.commit()
#     def get_sales_stats(self, days=30):
#         start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
#         return {
#             'total': self.conn.execute("SELECT COALESCE(SUM(total_price), 0) FROM sales").fetchone()[0],
#             'period': self.conn.execute("SELECT COALESCE(SUM(total_price), 0) FROM sales WHERE sale_date >= ?", (start,)).fetchone()[0],
#             'items': self.conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM sales").fetchone()[0]}

#     # === STATS ===
#     def get_monthly_production(self, months=6):
#         data = []
#         for i in range(months-1, -1, -1):
#             date = datetime.now() - timedelta(days=30*i)
#             start = date.replace(day=1).strftime('%Y-%m-%d')
#             end = (date.replace(day=1) + timedelta(days=32)).replace(day=1).strftime('%Y-%m-%d')
#             val = self.conn.execute("SELECT COALESCE(SUM(quantity_kg), 0) FROM production_log WHERE production_date >= ? AND production_date < ?", (start, end)).fetchone()[0]
#             data.append({'month': date.strftime('%b'), 'value': val})
#         return data
#     def get_stock_forecast(self):
#         forecasts = []
#         for c in self.get_all_colors():
#             avg = self.conn.execute("SELECT AVG(daily) FROM (SELECT DATE(movement_date) as d, SUM(quantity_kg) as daily FROM stock_movements WHERE color_id = ? AND movement_type = 'sortie' AND movement_date >= date('now', '-30 days') GROUP BY d)", (c['id'],)).fetchone()[0]
#             if avg and avg > 0:
#                 days = c['stock_kg'] / avg
#                 forecasts.append({'color': c['name'], 'hex': c['hex_code'], 'stock': c['stock_kg'], 'daily': avg, 'days': int(days), 'alert': days < 7})
#         return sorted(forecasts, key=lambda x: x['days'])

#     def backup(self):
#         os.makedirs(BACKUP_DIR, exist_ok=True)
#         path = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
#         shutil.copy2(DB_PATH, path); return path
#     def close(self): self.conn.close()



# # ============================================================================
# # DIALOGUE CONFIGURATION SMTP
# # ============================================================================
# class SMTPConfigDialog(ctk.CTkToplevel):
#     """Configuration SMTP avec test de connexion."""
    
#     def __init__(self, parent, on_save=None):
#         super().__init__(parent)
#         self.title("⚙️ Configuration SMTP")
#         self.geometry("550x620")
#         self.on_save = on_save
#         self.config = load_smtp_config()
        
#         ctk.CTkLabel(self, text="⚙️ Configuration Email SMTP", font=("Helvetica", 18, "bold")).pack(pady=15)
        
#         # Warning si pas de mot de passe
#         if not self.config.get('password'):
#             warn = ctk.CTkFrame(self, fg_color="#5a3030")
#             warn.pack(fill="x", padx=20, pady=5)
#             ctk.CTkLabel(warn, text="⚠️ Mot de passe non configuré - Les emails ne fonctionneront pas!", 
#                 text_color="#ff6b6b", font=("Helvetica", 11, "bold")).pack(pady=8)
        
#         scroll = ctk.CTkScrollableFrame(self)
#         scroll.pack(fill="both", expand=True, padx=20, pady=5)
        
#         # === SERVEUR ===
#         ctk.CTkLabel(scroll, text="📡 Serveur SMTP", font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(10, 5))
        
#         f1 = ctk.CTkFrame(scroll, fg_color="transparent"); f1.pack(fill="x", pady=3)
#         ctk.CTkLabel(f1, text="Hôte:", width=110, anchor="w").pack(side="left")
#         self.host = ctk.CTkEntry(f1, width=320, height=35)
#         self.host.pack(side="left", padx=5)
#         self.host.insert(0, self.config.get('host', 'smtp.hostinger.com'))
        
#         f2 = ctk.CTkFrame(scroll, fg_color="transparent"); f2.pack(fill="x", pady=3)
#         ctk.CTkLabel(f2, text="Port:", width=110, anchor="w").pack(side="left")
#         self.port = ctk.CTkEntry(f2, width=100, height=35)
#         self.port.pack(side="left", padx=5)
#         self.port.insert(0, str(self.config.get('port', 465)))
        
#         f3 = ctk.CTkFrame(scroll, fg_color="transparent"); f3.pack(fill="x", pady=5)
#         ctk.CTkLabel(f3, text="Sécurité:", width=110, anchor="w").pack(side="left")
#         self.security = ctk.CTkSegmentedButton(f3, values=["SSL (port 465)", "TLS (port 587)"], width=250)
#         self.security.pack(side="left", padx=5)
#         self.security.set("SSL (port 465)" if self.config.get('use_ssl', True) else "TLS (port 587)")
        
#         # === AUTHENTIFICATION ===
#         ctk.CTkLabel(scroll, text="🔐 Authentification", font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(20, 5))
        
#         f4 = ctk.CTkFrame(scroll, fg_color="transparent"); f4.pack(fill="x", pady=3)
#         ctk.CTkLabel(f4, text="Email:", width=110, anchor="w").pack(side="left")
#         self.username = ctk.CTkEntry(f4, width=320, height=35)
#         self.username.pack(side="left", padx=5)
#         self.username.insert(0, self.config.get('username', 'contact@krysto.io'))
        
#         f5 = ctk.CTkFrame(scroll, fg_color="transparent"); f5.pack(fill="x", pady=3)
#         ctk.CTkLabel(f5, text="Mot de passe:", width=110, anchor="w").pack(side="left")
#         self.password = ctk.CTkEntry(f5, width=320, height=35, show="●")
#         self.password.pack(side="left", padx=5)
#         self.password.insert(0, self.config.get('password', ''))
        
#         # Toggle show password
#         self.show_pwd = ctk.CTkCheckBox(scroll, text="Afficher le mot de passe", command=self._toggle_pwd)
#         self.show_pwd.pack(anchor="w", pady=5, padx=5)
        
#         # === EXPÉDITEUR ===
#         ctk.CTkLabel(scroll, text="📧 Expéditeur", font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(20, 5))
        
#         f6 = ctk.CTkFrame(scroll, fg_color="transparent"); f6.pack(fill="x", pady=3)
#         ctk.CTkLabel(f6, text="Nom affiché:", width=110, anchor="w").pack(side="left")
#         self.from_name = ctk.CTkEntry(f6, width=320, height=35)
#         self.from_name.pack(side="left", padx=5)
#         self.from_name.insert(0, self.config.get('from_name', COMPANY_NAME))
        
#         # === INFO ===
#         info = ctk.CTkFrame(scroll, fg_color=KRYSTO_DARK)
#         info.pack(fill="x", pady=15)
#         ctk.CTkLabel(info, text="💡 Pour Hostinger:\n"
#             "• Serveur: smtp.hostinger.com\n"
#             "• Port: 465 avec SSL\n"
#             "• Le mot de passe est celui de votre boîte email Hostinger", 
#             text_color="#888", font=("Helvetica", 10), justify="left").pack(pady=10, padx=10)
        
#         # === BOUTONS ===
#         bf = ctk.CTkFrame(self, fg_color="transparent")
#         bf.pack(fill="x", padx=20, pady=15)
        
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, 
#             fg_color="#6c757d", width=90, height=38).pack(side="left")
        
#         ctk.CTkButton(bf, text="🧪 Tester la connexion", command=self._test,
#             fg_color="#F77F00", width=170, height=38).pack(side="left", padx=15)
        
#         ctk.CTkButton(bf, text="💾 Sauvegarder", command=self._save,
#             fg_color=KRYSTO_PRIMARY, width=140, height=38).pack(side="right")
        
#         self.grab_set()
#         self.focus_force()
    
#     def _toggle_pwd(self):
#         self.password.configure(show="" if self.show_pwd.get() else "●")
    
#     def _get_config(self):
#         sec = self.security.get()
#         return {
#             'host': self.host.get().strip(),
#             'port': int(self.port.get() or 465),
#             'use_ssl': "SSL" in sec,
#             'username': self.username.get().strip(),
#             'password': self.password.get(),
#             'from_name': self.from_name.get().strip() or COMPANY_NAME
#         }
    
#     def _test(self):
#         config = self._get_config()
        
#         if not config['password']:
#             messagebox.showwarning("⚠️ Mot de passe manquant", 
#                 "Veuillez entrer le mot de passe de votre boîte email!")
#             return
        
#         # Fenêtre de test
#         test_win = ctk.CTkToplevel(self)
#         test_win.title("Test connexion")
#         test_win.geometry("420x200")
#         test_win.transient(self)
        
#         ctk.CTkLabel(test_win, text="🔄 Test de connexion en cours...", 
#             font=("Helvetica", 14)).pack(pady=25)
        
#         progress = ctk.CTkProgressBar(test_win, width=320)
#         progress.pack(pady=10)
#         progress.configure(mode="indeterminate")
#         progress.start()
        
#         status_lbl = ctk.CTkLabel(test_win, text=f"Connexion à {config['host']}:{config['port']}...", 
#             text_color="#888")
#         status_lbl.pack(pady=5)
        
#         def do_test():
#             service = EmailService(config)
#             success, msg = service.test_connection()
            
#             try:
#                 test_win.destroy()
#             except: pass
            
#             if success:
#                 messagebox.showinfo("✅ Connexion réussie!", 
#                     f"La connexion SMTP fonctionne!\n\n"
#                     f"Serveur: {config['host']}\n"
#                     f"Email: {config['username']}\n\n"
#                     "Vous pouvez maintenant envoyer des emails.")
#             else:
#                 messagebox.showerror("❌ Échec de connexion", msg)
        
#         threading.Thread(target=do_test, daemon=True).start()
    
#     def _save(self):
#         config = self._get_config()
        
#         if not config['password']:
#             if not messagebox.askyesno("⚠️ Attention", 
#                 "Aucun mot de passe configuré!\n\n"
#                 "Les emails ne fonctionneront pas.\n\n"
#                 "Sauvegarder quand même?"):
#                 return
        
#         if save_smtp_config(config):
#             if self.on_save:
#                 self.on_save(config)
#             messagebox.showinfo("✅ Sauvegardé", 
#                 f"Configuration SMTP sauvegardée!\n\n"
#                 f"Fichier: {SMTP_CONFIG_FILE}")
#             self.destroy()
#         else:
#             messagebox.showerror("Erreur", "Impossible de sauvegarder la configuration")




# # ============================================================================
# # ÉDITEUR D'EMAIL VISUEL - BLOCS
# # ============================================================================

# class EmailBlock:
#     """Classe de base pour les blocs d'email."""
#     def __init__(self, block_type, content=None):
#         self.block_type = block_type
#         self.content = content or {}
    
#     def to_html(self):
#         return ""
    
#     def get_preview_text(self):
#         return self.block_type

# class TextBlock(EmailBlock):
#     def __init__(self, text="", font_size=15, color=KRYSTO_DARK, bold=False, centered=False):
#         super().__init__("text", {
#             "text": text, "font_size": font_size, "color": color, "bold": bold, "centered": centered
#         })
    
#     def to_html(self):
#         c = self.content
#         style = f"font-size: {c['font_size']}px; color: {c['color']}; line-height: 1.8; margin: 15px 0;"
#         if c['bold']: style += " font-weight: bold;"
#         if c['centered']: style += " text-align: center;"
#         text = c['text'].replace('\n', '<br>')
#         return f'<div style="{style}">{text}</div>'
    
#     def get_preview_text(self):
#         t = self.content['text'][:50]
#         return f"📝 {t}..." if len(self.content['text']) > 50 else f"📝 {t}"

# class TitleBlock(EmailBlock):
#     def __init__(self, text="", font_size=24, color=KRYSTO_DARK):
#         super().__init__("title", {"text": text, "font_size": font_size, "color": color})
    
#     def to_html(self):
#         c = self.content
#         return f'''<h2 style="margin: 25px 0 15px 0; color: {c['color']}; font-size: {c['font_size']}px; 
#             border-bottom: 3px solid {KRYSTO_SECONDARY}; padding-bottom: 12px;">{c['text']}</h2>'''
    
#     def get_preview_text(self):
#         return f"📌 {self.content['text']}"

# class ImageBlock(EmailBlock):
#     def __init__(self, url="", alt="Image", width="100%", centered=True):
#         super().__init__("image", {"url": url, "alt": alt, "width": width, "centered": centered})
    
#     def to_html(self):
#         c = self.content
#         if not c['url']: return ""
#         align = "center" if c['centered'] else "left"
#         return f'''<div style="text-align: {align}; margin: 20px 0;">
#             <img src="{c['url']}" alt="{c['alt']}" style="max-width: {c['width']}; height: auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
#         </div>'''
    
#     def get_preview_text(self):
#         return f"🖼️ Image: {self.content['url'][:30]}..."

# class ButtonBlock(EmailBlock):
#     def __init__(self, text="Cliquez ici", url="", bg_color=None, text_color="#ffffff"):
#         super().__init__("button", {
#             "text": text, "url": url or f"https://{COMPANY_WEBSITE}",
#             "bg_color": bg_color or KRYSTO_PRIMARY, "text_color": text_color
#         })
    
#     def to_html(self):
#         c = self.content
#         return f'''<div style="text-align: center; margin: 25px 0;">
#             <a href="{c['url']}" style="display: inline-block; padding: 14px 40px; 
#                background: linear-gradient(135deg, {KRYSTO_PRIMARY} 0%, {KRYSTO_SECONDARY} 100%); 
#                color: {c['text_color']}; text-decoration: none; border-radius: 25px; 
#                font-weight: bold; font-size: 15px; box-shadow: 0 4px 15px rgba(109, 116, 171, 0.4);">
#                {c['text']}
#             </a>
#         </div>'''
    
#     def get_preview_text(self):
#         return f"🔘 Bouton: {self.content['text']}"

# class SeparatorBlock(EmailBlock):
#     def __init__(self, style="gradient"):
#         super().__init__("separator", {"style": style})
    
#     def to_html(self):
#         if self.content['style'] == "gradient":
#             return f'''<div style="height: 4px; margin: 25px 0; 
#                 background: linear-gradient(90deg, {KRYSTO_SECONDARY}, {KRYSTO_PRIMARY}, {KRYSTO_SECONDARY}); 
#                 border-radius: 2px;"></div>'''
#         elif self.content['style'] == "simple":
#             return '<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 25px 0;">'
#         return '<div style="height: 20px;"></div>'
    
#     def get_preview_text(self):
#         return f"➖ Séparateur ({self.content['style']})"

# class SpacerBlock(EmailBlock):
#     def __init__(self, height=30):
#         super().__init__("spacer", {"height": height})
    
#     def to_html(self):
#         return f'<div style="height: {self.content["height"]}px;"></div>'
    
#     def get_preview_text(self):
#         return f"📏 Espace ({self.content['height']}px)"


# class EmailDesigner:
#     """Générateur d'email à partir de blocs."""
    
#     def __init__(self):
#         self.blocks = []
#         self.subject = ""
#         self.header_style = "gradient"
#         self.show_footer = True
    
#     def add_block(self, block):
#         self.blocks.append(block)
#         return self
    
#     def remove_block(self, index):
#         if 0 <= index < len(self.blocks):
#             self.blocks.pop(index)
    
#     def move_block_up(self, index):
#         if index > 0:
#             self.blocks[index], self.blocks[index-1] = self.blocks[index-1], self.blocks[index]
    
#     def move_block_down(self, index):
#         if index < len(self.blocks) - 1:
#             self.blocks[index], self.blocks[index+1] = self.blocks[index+1], self.blocks[index]
    
#     def clear(self):
#         self.blocks = []
    
#     def generate_html(self, recipient_name="Client", recipient_email=""):
#         if self.header_style == "gradient":
#             header = f'''<tr>
#                 <td style="background: linear-gradient(135deg, {KRYSTO_PRIMARY} 0%, {KRYSTO_SECONDARY} 100%); padding: 35px 40px; text-align: center;">
#                     <div style="font-size: 45px; margin-bottom: 10px;">♻️</div>
#                     <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: bold; letter-spacing: 1px;">{COMPANY_NAME}</h1>
#                     <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">Recyclage Plastique • Nouvelle-Calédonie</p>
#                 </td>
#             </tr>'''
#         elif self.header_style == "simple":
#             header = f'''<tr>
#                 <td style="background-color: {KRYSTO_DARK}; padding: 25px 40px; text-align: center;">
#                     <h1 style="margin: 0; color: {KRYSTO_SECONDARY}; font-size: 28px;">♻️ {COMPANY_NAME}</h1>
#                 </td>
#             </tr>'''
#         else:
#             header = ""
        
#         content_html = ""
#         for block in self.blocks:
#             html = block.to_html()
#             html = html.replace("{{name}}", recipient_name)
#             html = html.replace("{{email}}", recipient_email)
#             html = html.replace("{{date}}", datetime.now().strftime("%d/%m/%Y"))
#             content_html += html
        
#         if self.show_footer:
#             footer = f'''<tr>
#                 <td style="padding: 0 40px;">
#                     <div style="height: 3px; background: linear-gradient(90deg, {KRYSTO_SECONDARY}, {KRYSTO_PRIMARY}, {KRYSTO_SECONDARY}); border-radius: 2px;"></div>
#                 </td>
#             </tr>
#             <tr>
#                 <td style="padding: 30px 40px; background-color: #fafafa;">
#                     <table role="presentation" style="width: 100%;">
#                         <tr>
#                             <td style="color: #666666; font-size: 13px;">
#                                 <p style="margin: 0 0 10px 0; font-weight: bold; color: {KRYSTO_PRIMARY};">{COMPANY_NAME}</p>
#                                 <p style="margin: 0 0 5px 0;">📍 {COMPANY_ADDRESS}</p>
#                                 <p style="margin: 0 0 5px 0;">📧 {COMPANY_EMAIL}</p>
#                                 <p style="margin: 0;">🌐 {COMPANY_WEBSITE}</p>
#                             </td>
#                             <td align="right" valign="top">
#                                 <p style="margin: 0; color: #999999; font-size: 11px;">© {datetime.now().year} {COMPANY_NAME}</p>
#                             </td>
#                         </tr>
#                     </table>
#                 </td>
#             </tr>'''
#         else:
#             footer = ""
        
#         return f'''<!DOCTYPE html>
# <html lang="fr">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>{self.subject}</title>
# </head>
# <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
#     <table role="presentation" style="width: 100%; border-collapse: collapse;">
#         <tr>
#             <td align="center" style="padding: 40px 0;">
#                 <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); overflow: hidden;">
#                     {header}
#                     <tr>
#                         <td style="padding: 40px;">
#                             {content_html}
#                         </td>
#                     </tr>
#                     {footer}
#                 </table>
#                 <p style="margin: 25px 0 0 0; color: #999999; font-size: 11px;">
#                     Vous recevez cet email car vous êtes client {COMPANY_NAME}.<br>
#                     <a href="#" style="color: {KRYSTO_PRIMARY};">Se désinscrire</a>
#                 </p>
#             </td>
#         </tr>
#     </table>
# </body>
# </html>'''


# class BlockEditorDialog(ctk.CTkToplevel):
#     """Dialogue pour éditer un bloc."""
    
#     def __init__(self, parent, block_type, existing_block=None, on_save=None):
#         super().__init__(parent)
#         self.title(f"{'Modifier' if existing_block else 'Ajouter'} - {block_type}")
#         self.geometry("550x450")
#         self.block_type = block_type
#         self.existing_block = existing_block
#         self.on_save = on_save
#         self.result = None
#         self._init_ui()
#         self.grab_set()
    
#     def _init_ui(self):
#         main = ctk.CTkScrollableFrame(self)
#         main.pack(fill="both", expand=True, padx=20, pady=20)
        
#         if self.block_type == "text":
#             self._ui_text(main)
#         elif self.block_type == "title":
#             self._ui_title(main)
#         elif self.block_type == "image":
#             self._ui_image(main)
#         elif self.block_type == "button":
#             self._ui_button(main)
#         elif self.block_type == "separator":
#             self._ui_separator(main)
#         elif self.block_type == "spacer":
#             self._ui_spacer(main)
        
#         bf = ctk.CTkFrame(self, fg_color="transparent")
#         bf.pack(fill="x", padx=20, pady=15)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=100).pack(side="left")
#         ctk.CTkButton(bf, text="✅ Valider", command=self._save, fg_color=KRYSTO_PRIMARY, width=120).pack(side="right")
    
#     def _ui_text(self, parent):
#         ctk.CTkLabel(parent, text="📝 Bloc Texte", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
#         ctk.CTkLabel(parent, text="Contenu:").pack(anchor="w", pady=(10, 5))
#         self.text_content = ctk.CTkTextbox(parent, height=180)
#         self.text_content.pack(fill="x")
#         ctk.CTkLabel(parent, text="Variables: {{name}} {{email}} {{date}}", text_color="#888", font=("Helvetica", 10)).pack(anchor="w", pady=5)
        
#         row1 = ctk.CTkFrame(parent, fg_color="transparent"); row1.pack(fill="x", pady=10)
#         ctk.CTkLabel(row1, text="Taille:").pack(side="left")
#         self.font_size = ctk.CTkEntry(row1, width=50); self.font_size.pack(side="left", padx=5)
#         self.font_size.insert(0, "15")
#         self.bold_var = ctk.BooleanVar(value=False)
#         ctk.CTkCheckBox(row1, text="Gras", variable=self.bold_var).pack(side="left", padx=10)
#         self.centered_var = ctk.BooleanVar(value=False)
#         ctk.CTkCheckBox(row1, text="Centré", variable=self.centered_var).pack(side="left")
        
#         if self.existing_block:
#             c = self.existing_block.content
#             self.text_content.insert("1.0", c.get('text', ''))
#             self.font_size.delete(0, "end"); self.font_size.insert(0, str(c.get('font_size', 15)))
#             self.bold_var.set(c.get('bold', False)); self.centered_var.set(c.get('centered', False))
    
#     def _ui_title(self, parent):
#         ctk.CTkLabel(parent, text="📌 Bloc Titre", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
#         ctk.CTkLabel(parent, text="Titre:").pack(anchor="w", pady=(10, 5))
#         self.title_text = ctk.CTkEntry(parent, height=38); self.title_text.pack(fill="x")
#         row1 = ctk.CTkFrame(parent, fg_color="transparent"); row1.pack(fill="x", pady=15)
#         ctk.CTkLabel(row1, text="Taille:").pack(side="left")
#         self.title_size = ctk.CTkEntry(row1, width=60); self.title_size.pack(side="left", padx=10)
#         self.title_size.insert(0, "24")
#         if self.existing_block:
#             c = self.existing_block.content
#             self.title_text.insert(0, c.get('text', ''))
#             self.title_size.delete(0, "end"); self.title_size.insert(0, str(c.get('font_size', 24)))
    
#     def _ui_image(self, parent):
#         ctk.CTkLabel(parent, text="🖼️ Bloc Image", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
#         ctk.CTkLabel(parent, text="URL de l'image:").pack(anchor="w", pady=(10, 5))
#         self.image_url = ctk.CTkEntry(parent, height=38, placeholder_text="https://exemple.com/image.jpg")
#         self.image_url.pack(fill="x")
#         ctk.CTkLabel(parent, text="💡 Hébergeurs: imgur.com, imgbb.com, postimages.org", text_color="#888", font=("Helvetica", 10)).pack(anchor="w", pady=5)
        
#         row1 = ctk.CTkFrame(parent, fg_color="transparent"); row1.pack(fill="x", pady=10)
#         ctk.CTkLabel(row1, text="Largeur:").pack(side="left")
#         self.image_width = ctk.CTkEntry(row1, width=80); self.image_width.pack(side="left", padx=10)
#         self.image_width.insert(0, "100%")
#         self.image_centered = ctk.BooleanVar(value=True)
#         ctk.CTkCheckBox(row1, text="Centré", variable=self.image_centered).pack(side="left", padx=10)
        
#         ctk.CTkLabel(parent, text="Texte alternatif:").pack(anchor="w", pady=(10, 5))
#         self.image_alt = ctk.CTkEntry(parent, height=35); self.image_alt.pack(fill="x")
#         self.image_alt.insert(0, "Image")
        
#         if self.existing_block:
#             c = self.existing_block.content
#             self.image_url.insert(0, c.get('url', ''))
#             self.image_width.delete(0, "end"); self.image_width.insert(0, c.get('width', '100%'))
#             self.image_alt.delete(0, "end"); self.image_alt.insert(0, c.get('alt', 'Image'))
#             self.image_centered.set(c.get('centered', True))
    
#     def _ui_button(self, parent):
#         ctk.CTkLabel(parent, text="🔘 Bloc Bouton", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
#         ctk.CTkLabel(parent, text="Texte du bouton:").pack(anchor="w", pady=(10, 5))
#         self.btn_text = ctk.CTkEntry(parent, height=38); self.btn_text.pack(fill="x")
#         self.btn_text.insert(0, "Cliquez ici")
#         ctk.CTkLabel(parent, text="URL (lien):").pack(anchor="w", pady=(15, 5))
#         self.btn_url = ctk.CTkEntry(parent, height=38, placeholder_text=f"https://{COMPANY_WEBSITE}")
#         self.btn_url.pack(fill="x")
#         if self.existing_block:
#             c = self.existing_block.content
#             self.btn_text.delete(0, "end"); self.btn_text.insert(0, c.get('text', 'Cliquez ici'))
#             self.btn_url.insert(0, c.get('url', ''))
    
#     def _ui_separator(self, parent):
#         ctk.CTkLabel(parent, text="➖ Bloc Séparateur", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
#         ctk.CTkLabel(parent, text="Style:").pack(anchor="w", pady=(10, 5))
#         self.sep_style = ctk.CTkSegmentedButton(parent, values=["gradient", "simple", "espace"])
#         self.sep_style.pack(fill="x"); self.sep_style.set("gradient")
#         if self.existing_block:
#             self.sep_style.set(self.existing_block.content.get('style', 'gradient'))
    
#     def _ui_spacer(self, parent):
#         ctk.CTkLabel(parent, text="📏 Bloc Espace", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 15))
#         ctk.CTkLabel(parent, text="Hauteur (pixels):").pack(anchor="w", pady=(10, 5))
#         self.spacer_height = ctk.CTkEntry(parent, width=80); self.spacer_height.pack(anchor="w")
#         self.spacer_height.insert(0, "30")
#         if self.existing_block:
#             self.spacer_height.delete(0, "end")
#             self.spacer_height.insert(0, str(self.existing_block.content.get('height', 30)))
    
#     def _save(self):
#         if self.block_type == "text":
#             self.result = TextBlock(
#                 text=self.text_content.get("1.0", "end-1c"),
#                 font_size=int(self.font_size.get() or 15),
#                 bold=self.bold_var.get(),
#                 centered=self.centered_var.get()
#             )
#         elif self.block_type == "title":
#             self.result = TitleBlock(
#                 text=self.title_text.get(),
#                 font_size=int(self.title_size.get() or 24)
#             )
#         elif self.block_type == "image":
#             self.result = ImageBlock(
#                 url=self.image_url.get(),
#                 alt=self.image_alt.get(),
#                 width=self.image_width.get(),
#                 centered=self.image_centered.get()
#             )
#         elif self.block_type == "button":
#             self.result = ButtonBlock(
#                 text=self.btn_text.get(),
#                 url=self.btn_url.get() or f"https://{COMPANY_WEBSITE}"
#             )
#         elif self.block_type == "separator":
#             self.result = SeparatorBlock(style=self.sep_style.get())
#         elif self.block_type == "spacer":
#             self.result = SpacerBlock(height=int(self.spacer_height.get() or 30))
        
#         if self.on_save:
#             self.on_save(self.result)
#         self.destroy()


# # ============================================================================
# # FRAME MAILING AMÉLIORÉ avec éditeur visuel
# # ============================================================================
# class MailingFrame(ctk.CTkFrame):
#     """Interface de mailing avec éditeur visuel et prévisualisation."""
    
#     def __init__(self, parent, db, on_back):
#         super().__init__(parent)
#         self.db = db
#         self.on_back = on_back
#         self.smtp_config = load_smtp_config()
#         self.email_service = EmailService(self.smtp_config)
#         self.designer = EmailDesigner()
        
#         self._init_ui()
#         self.refresh_stats()
    
#     def _init_ui(self):
#         # Header
#         hdr = ctk.CTkFrame(self, fg_color="transparent")
#         hdr.pack(fill="x", padx=20, pady=10)
        
#         ctk.CTkButton(hdr, text="← Retour", command=self.on_back, 
#             width=90, fg_color="#6c757d").pack(side="left")
        
#         ctk.CTkLabel(hdr, text=f"📧 Mailing {COMPANY_NAME}", 
#             font=("Helvetica", 18, "bold")).pack(side="left", padx=12)
        
#         ctk.CTkButton(hdr, text="⚙️ Configurer SMTP", command=self._config_smtp,
#             fg_color=KRYSTO_PRIMARY, width=150, height=35).pack(side="right")
        
#         # Status SMTP
#         self.smtp_status_frame = ctk.CTkFrame(self, fg_color=KRYSTO_DARK)
#         self.smtp_status_frame.pack(fill="x", padx=20, pady=5)
#         self._update_smtp_status()
        
#         # Stats clients
#         self.stats_frame = ctk.CTkFrame(self)
#         self.stats_frame.pack(fill="x", padx=20, pady=5)
        
#         # Tabs
#         self.tabs = ctk.CTkTabview(self)
#         self.tabs.pack(fill="both", expand=True, padx=20, pady=5)
        
#         self.t_compose = self.tabs.add("✏️ Composer")
#         self.t_designer = self.tabs.add("🎨 Éditeur Visuel")
#         self.t_templates = self.tabs.add("📑 Templates")
#         self.t_history = self.tabs.add("📋 Historique")
        
#         self._build_compose_tab()
#         self._build_designer_tab()
#         self._build_templates_tab()
#         self._build_history_tab()
    
#     def _update_smtp_status(self):
#         for w in self.smtp_status_frame.winfo_children():
#             w.destroy()
        
#         sf = ctk.CTkFrame(self.smtp_status_frame, fg_color="transparent")
#         sf.pack(fill="x", padx=15, pady=10)
        
#         host = self.smtp_config.get('host', 'Non configuré')
#         user = self.smtp_config.get('username', '')
#         has_pwd = bool(self.smtp_config.get('password'))
        
#         if has_pwd:
#             status_text = "✅ SMTP configuré et prêt"
#             status_color = KRYSTO_SECONDARY
#         else:
#             status_text = "⚠️ MOT DE PASSE MANQUANT - Cliquez sur 'Configurer SMTP'"
#             status_color = "#ff6b6b"
        
#         ctk.CTkLabel(sf, text=f"📧 {host}", text_color="#888", 
#             font=("Helvetica", 10)).pack(side="left")
#         ctk.CTkLabel(sf, text=f" | {user}", text_color="#666", 
#             font=("Helvetica", 10)).pack(side="left")
        
#         status_lbl = ctk.CTkLabel(sf, text=f" | {status_text}", text_color=status_color,
#             font=("Helvetica", 11, "bold"))
#         status_lbl.pack(side="left", padx=10)
        
#         if has_pwd:
#             ctk.CTkButton(sf, text="🧪 Tester", width=80, height=28,
#                 fg_color="#F77F00", command=self._quick_test_smtp).pack(side="right")
    
#     def refresh_stats(self):
#         for w in self.stats_frame.winfo_children():
#             w.destroy()
        
#         stats = self.db.get_client_stats()
        
#         sr = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
#         sr.pack(fill="x", pady=4)
        
#         data = [
#             ("Total clients", str(stats['total']), KRYSTO_PRIMARY),
#             ("Pro 🏢", str(stats['pro']), KRYSTO_SECONDARY),
#             ("Part. 👤", str(stats['particulier']), "#F77F00"),
#             ("Avec email", str(stats['with_email']), "#4CAF50"),
#             ("Inscrits NL", str(stats['subscribed']), KRYSTO_PRIMARY)
#         ]
        
#         for lbl, val, col in data:
#             box = ctk.CTkFrame(sr, fg_color=KRYSTO_DARK)
#             box.pack(side="left", expand=True, fill="x", padx=2)
#             ctk.CTkLabel(box, text=lbl, text_color="#888", font=("Helvetica", 9)).pack(pady=(6, 0))
#             ctk.CTkLabel(box, text=val, font=("Helvetica", 14, "bold"), text_color=col).pack(pady=(0, 6))
    
#     def _build_compose_tab(self):
#         scroll = ctk.CTkScrollableFrame(self.t_compose)
#         scroll.pack(fill="both", expand=True)
        
#         # Destinataires
#         dest = ctk.CTkFrame(scroll, fg_color=KRYSTO_DARK)
#         dest.pack(fill="x", pady=5, padx=5)
        
#         df = ctk.CTkFrame(dest, fg_color="transparent")
#         df.pack(fill="x", padx=15, pady=10)
        
#         ctk.CTkLabel(df, text="📬 Destinataires", font=("Helvetica", 12, "bold")).pack(side="left")
        
#         self.dest_type = ctk.CTkSegmentedButton(df, 
#             values=["Tous", "Pro 🏢", "Part. 👤"],
#             command=self._update_recipient_count)
#         self.dest_type.pack(side="left", padx=20)
#         self.dest_type.set("Tous")
        
#         self.count_lbl = ctk.CTkLabel(df, text="0 destinataires", 
#             text_color=KRYSTO_SECONDARY, font=("Helvetica", 12, "bold"))
#         self.count_lbl.pack(side="right")
        
#         # Sujet
#         subj = ctk.CTkFrame(scroll, fg_color="transparent")
#         subj.pack(fill="x", pady=10, padx=5)
#         ctk.CTkLabel(subj, text="Sujet:", width=80, anchor="w", font=("Helvetica", 11)).pack(side="left")
#         self.subject = ctk.CTkEntry(subj, width=500, height=38, 
#             placeholder_text="Objet de l'email...", font=("Helvetica", 12))
#         self.subject.pack(side="left", padx=5)
        
#         # Type de template
#         tmpl = ctk.CTkFrame(scroll, fg_color="transparent")
#         tmpl.pack(fill="x", pady=5, padx=5)
#         ctk.CTkLabel(tmpl, text="Template:", width=80, anchor="w", font=("Helvetica", 11)).pack(side="left")
#         self.template_type = ctk.CTkSegmentedButton(tmpl, 
#             values=["📝 Simple", "📰 Newsletter", "🎁 Promo"],
#             command=self._on_template_change)
#         self.template_type.pack(side="left", padx=5)
#         self.template_type.set("📝 Simple")
        
#         # Container formulaires templates
#         self.form_container = ctk.CTkFrame(scroll, fg_color="transparent")
#         self.form_container.pack(fill="x", pady=10, padx=5)
        
#         # Formulaire Simple
#         self._build_simple_form()
        
#         # Formulaire Newsletter
#         self._build_newsletter_form()
        
#         # Formulaire Promo
#         self._build_promo_form()
        
#         # Afficher Simple par défaut
#         self.simple_frame.pack(fill="x")
        
#         # Boutons actions
#         btn = ctk.CTkFrame(scroll, fg_color="transparent")
#         btn.pack(fill="x", pady=15, padx=5)
        
#         ctk.CTkButton(btn, text="👁️ PRÉVISUALISER", 
#             command=self._preview_in_browser, fg_color=KRYSTO_PRIMARY, width=150, height=40,
#             font=("Helvetica", 12, "bold")).pack(side="left", padx=5)
        
#         ctk.CTkButton(btn, text="🧪 Email test", 
#             command=self._send_test, fg_color="#F77F00", width=120, height=40).pack(side="left", padx=5)
        
#         ctk.CTkButton(btn, text="📤 ENVOYER LA CAMPAGNE", 
#             command=self._send_campaign, fg_color=KRYSTO_SECONDARY, 
#             text_color=KRYSTO_DARK, width=220, height=45,
#             font=("Helvetica", 13, "bold")).pack(side="right", padx=5)
        
#         self._update_recipient_count()
    
#     def _build_simple_form(self):
#         self.simple_frame = ctk.CTkFrame(self.form_container, fg_color="transparent")
        
#         ctk.CTkLabel(self.simple_frame, text="Contenu de l'email (HTML supporté):", anchor="w", 
#             font=("Helvetica", 11)).pack(anchor="w", pady=(5, 2))
#         ctk.CTkLabel(self.simple_frame, text="💡 Variables disponibles: {{name}} = nom du client, {{email}}, {{date}}", 
#             text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
        
#         self.simple_content = ctk.CTkTextbox(self.simple_frame, height=200, font=("Helvetica", 11))
#         self.simple_content.pack(fill="x", pady=5)
#         self.simple_content.insert("1.0", f"""<p>Bonjour {{{{name}}}},</p>

# <p>Nous avons le plaisir de vous informer de nos dernières nouveautés chez {COMPANY_NAME}.</p>

# <p>En tant que spécialiste du <strong>recyclage plastique</strong> en Nouvelle-Calédonie, nous développons des produits éco-responsables uniques.</p>

# <p>N'hésitez pas à nous contacter pour plus d'informations.</p>

# <p>Cordialement,<br><strong>L'équipe {COMPANY_NAME}</strong></p>""")
        
#         cf = ctk.CTkFrame(self.simple_frame, fg_color="transparent")
#         cf.pack(fill="x", pady=5)
#         self.show_button = ctk.CTkCheckBox(cf, text="Afficher le bouton 'Visitez notre site'")
#         self.show_button.pack(side="left")
#         self.show_button.select()
    
#     def _build_newsletter_form(self):
#         self.newsletter_frame = ctk.CTkFrame(self.form_container, fg_color="transparent")
        
#         ctk.CTkLabel(self.newsletter_frame, text="Titre de la newsletter:", anchor="w").pack(anchor="w", pady=(5, 2))
#         self.nl_title = ctk.CTkEntry(self.newsletter_frame, width=500, height=35,
#             placeholder_text="Ex: Les actualités KRYSTO de janvier")
#         self.nl_title.pack(fill="x", pady=2)
        
#         ctk.CTkLabel(self.newsletter_frame, text="Introduction:", anchor="w").pack(anchor="w", pady=(10, 2))
#         self.nl_intro = ctk.CTkTextbox(self.newsletter_frame, height=60)
#         self.nl_intro.pack(fill="x", pady=2)
#         self.nl_intro.insert("1.0", "Découvrez toutes nos actualités ce mois-ci !")
        
#         ctk.CTkLabel(self.newsletter_frame, text="Sections (format: icône | titre | contenu - une par ligne):", 
#             anchor="w").pack(anchor="w", pady=(10, 2))
        
#         self.nl_sections = ctk.CTkTextbox(self.newsletter_frame, height=120)
#         self.nl_sections.pack(fill="x", pady=2)
#         self.nl_sections.insert("1.0", """🆕 | Nouveaux produits | Découvrez notre nouvelle gamme de pots recyclés.
# ♻️ | Impact écologique | Ce mois-ci, nous avons recyclé plus de 500kg de plastique !
# 📅 | Événements | Retrouvez-nous au marché de Nouméa ce week-end.""")
        
#         cf = ctk.CTkFrame(self.newsletter_frame, fg_color="transparent")
#         cf.pack(fill="x", pady=10)
#         ctk.CTkLabel(cf, text="Bouton CTA (optionnel):").pack(side="left")
#         self.nl_cta_text = ctk.CTkEntry(cf, width=150, placeholder_text="Texte du bouton")
#         self.nl_cta_text.pack(side="left", padx=5)
#         self.nl_cta_url = ctk.CTkEntry(cf, width=250, placeholder_text="URL (https://...)")
#         self.nl_cta_url.pack(side="left", padx=5)
    
#     def _build_promo_form(self):
#         self.promo_frame = ctk.CTkFrame(self.form_container, fg_color="transparent")
        
#         ctk.CTkLabel(self.promo_frame, text="Titre de la promotion:", anchor="w").pack(anchor="w", pady=(5, 2))
#         self.promo_title = ctk.CTkEntry(self.promo_frame, width=500, height=35,
#             placeholder_text="Ex: Offre spéciale -20% sur tous nos produits!")
#         self.promo_title.pack(fill="x", pady=2)
        
#         ctk.CTkLabel(self.promo_frame, text="Description de l'offre:", anchor="w").pack(anchor="w", pady=(10, 2))
#         self.promo_text = ctk.CTkTextbox(self.promo_frame, height=80)
#         self.promo_text.pack(fill="x", pady=2)
#         self.promo_text.insert("1.0", "Profitez de -20% sur tous nos produits recyclés ! Une occasion unique de faire un geste pour la planète tout en économisant.")
        
#         cf = ctk.CTkFrame(self.promo_frame, fg_color="transparent")
#         cf.pack(fill="x", pady=10)
        
#         ctk.CTkLabel(cf, text="Code promo:", width=90).pack(side="left")
#         self.promo_code = ctk.CTkEntry(cf, width=130, placeholder_text="KRYSTO20", font=("Helvetica", 12, "bold"))
#         self.promo_code.pack(side="left", padx=5)
        
#         ctk.CTkLabel(cf, text="Expire le:", width=80).pack(side="left", padx=(20, 0))
#         self.promo_expiry = ctk.CTkEntry(cf, width=120, placeholder_text="31/01/2026")
#         self.promo_expiry.pack(side="left", padx=5)
    
#     def _on_template_change(self, val):
#         # Cacher tous les formulaires
#         self.simple_frame.pack_forget()
#         self.newsletter_frame.pack_forget()
#         self.promo_frame.pack_forget()
        
#         # Afficher le bon formulaire
#         if val == "📝 Simple":
#             self.simple_frame.pack(fill="x")
#         elif val == "📰 Newsletter":
#             self.newsletter_frame.pack(fill="x")
#         elif val == "🎁 Promo":
#             self.promo_frame.pack(fill="x")
    
#     def _build_designer_tab(self):
#         """Construit l'onglet éditeur visuel avec gestion de blocs."""
#         # Header
#         hdr = ctk.CTkFrame(self.t_designer, fg_color=KRYSTO_DARK)
#         hdr.pack(fill="x", padx=5, pady=5)
        
#         hf = ctk.CTkFrame(hdr, fg_color="transparent")
#         hf.pack(fill="x", padx=15, pady=12)
        
#         ctk.CTkLabel(hf, text="🎨 Éditeur Visuel d'Email", 
#             font=("Helvetica", 14, "bold")).pack(side="left")
        
#         ctk.CTkLabel(hf, text="Créez votre email en ajoutant des blocs", 
#             text_color="#888", font=("Helvetica", 10)).pack(side="left", padx=15)
        
#         # Destinataires dans l'éditeur
#         dest_frame = ctk.CTkFrame(self.t_designer, fg_color="transparent")
#         dest_frame.pack(fill="x", padx=5, pady=5)
        
#         ctk.CTkLabel(dest_frame, text="📬 Destinataires:", font=("Helvetica", 11)).pack(side="left")
        
#         self.designer_dest_type = ctk.CTkSegmentedButton(dest_frame, 
#             values=["Tous", "Pro 🏢", "Part. 👤"],
#             command=self._update_designer_recipient_count)
#         self.designer_dest_type.pack(side="left", padx=10)
#         self.designer_dest_type.set("Tous")
        
#         self.designer_count_lbl = ctk.CTkLabel(dest_frame, text="0 destinataires", 
#             text_color=KRYSTO_SECONDARY, font=("Helvetica", 11, "bold"))
#         self.designer_count_lbl.pack(side="left", padx=10)
        
#         # Sujet
#         subj_frame = ctk.CTkFrame(self.t_designer, fg_color="transparent")
#         subj_frame.pack(fill="x", padx=5, pady=5)
#         ctk.CTkLabel(subj_frame, text="Sujet:", width=60).pack(side="left")
#         self.designer_subject = ctk.CTkEntry(subj_frame, width=500, height=35,
#             placeholder_text="Objet de l'email...")
#         self.designer_subject.pack(side="left", padx=5)
        
#         # Options header/footer
#         opt_frame = ctk.CTkFrame(self.t_designer, fg_color="transparent")
#         opt_frame.pack(fill="x", padx=5, pady=5)
        
#         ctk.CTkLabel(opt_frame, text="Header:").pack(side="left")
#         self.header_style = ctk.CTkSegmentedButton(opt_frame, 
#             values=["Gradient", "Simple", "Aucun"], width=200)
#         self.header_style.pack(side="left", padx=5)
#         self.header_style.set("Gradient")
        
#         self.show_footer_var = ctk.BooleanVar(value=True)
#         ctk.CTkCheckBox(opt_frame, text="Afficher footer KRYSTO", 
#             variable=self.show_footer_var).pack(side="left", padx=20)
        
#         # Zone principale avec 2 colonnes
#         main = ctk.CTkFrame(self.t_designer, fg_color="transparent")
#         main.pack(fill="both", expand=True, padx=5, pady=5)
        
#         # Colonne gauche: Ajout de blocs
#         left = ctk.CTkFrame(main, width=200, fg_color=KRYSTO_DARK)
#         left.pack(side="left", fill="y", padx=(0, 5))
#         left.pack_propagate(False)
        
#         ctk.CTkLabel(left, text="➕ Ajouter un bloc", 
#             font=("Helvetica", 12, "bold")).pack(pady=12)
        
#         block_types = [
#             ("📝 Texte", "text"),
#             ("📌 Titre", "title"),
#             ("🖼️ Image", "image"),
#             ("🔘 Bouton", "button"),
#             ("➖ Séparateur", "separator"),
#             ("📏 Espace", "spacer"),
#         ]
        
#         for label, btype in block_types:
#             ctk.CTkButton(left, text=label, fg_color=KRYSTO_PRIMARY, width=170, height=35,
#                 command=lambda t=btype: self._add_block_dialog(t)).pack(pady=3, padx=10)
        
#         ctk.CTkFrame(left, height=2, fg_color="#555").pack(fill="x", pady=15, padx=10)
        
#         ctk.CTkButton(left, text="🗑️ Tout effacer", fg_color="#dc3545", width=170, height=32,
#             command=self._clear_all_blocks).pack(pady=5, padx=10)
        
#         # Colonne droite: Liste des blocs
#         right = ctk.CTkFrame(main, fg_color="transparent")
#         right.pack(side="left", fill="both", expand=True)
        
#         ctk.CTkLabel(right, text="📋 Blocs de l'email", 
#             font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 8))
        
#         self.blocks_list_frame = ctk.CTkScrollableFrame(right, fg_color="#2b2b2b")
#         self.blocks_list_frame.pack(fill="both", expand=True)
        
#         # Message si vide
#         self.empty_blocks_label = ctk.CTkLabel(self.blocks_list_frame, 
#             text="Aucun bloc ajouté\nCliquez sur les boutons à gauche pour ajouter des éléments",
#             text_color="#888", font=("Helvetica", 11))
#         self.empty_blocks_label.pack(pady=50)
        
#         # Boutons actions en bas
#         btn_frame = ctk.CTkFrame(self.t_designer, fg_color="transparent")
#         btn_frame.pack(fill="x", padx=5, pady=10)
        
#         ctk.CTkButton(btn_frame, text="👁️ PRÉVISUALISER", 
#             command=self._preview_designer_email, fg_color=KRYSTO_PRIMARY, 
#             width=160, height=42, font=("Helvetica", 12, "bold")).pack(side="left", padx=5)
        
#         ctk.CTkButton(btn_frame, text="🧪 Email test", 
#             command=self._send_designer_test, fg_color="#F77F00", 
#             width=130, height=42).pack(side="left", padx=5)
        
#         ctk.CTkButton(btn_frame, text="📤 ENVOYER LA CAMPAGNE", 
#             command=self._send_designer_campaign, fg_color=KRYSTO_SECONDARY, 
#             text_color=KRYSTO_DARK, width=220, height=45,
#             font=("Helvetica", 13, "bold")).pack(side="right", padx=5)
        
#         self._update_designer_recipient_count()
    
#     def _add_block_dialog(self, block_type):
#         """Ouvre le dialogue pour ajouter un bloc."""
#         def on_save(block):
#             if block:
#                 self.designer.add_block(block)
#                 self._refresh_blocks_list()
        
#         BlockEditorDialog(self, block_type, on_save=on_save)
    
#     def _edit_block(self, index):
#         """Édite un bloc existant."""
#         block = self.designer.blocks[index]
#         def on_save(new_block):
#             if new_block:
#                 self.designer.blocks[index] = new_block
#                 self._refresh_blocks_list()
        
#         BlockEditorDialog(self, block.block_type, existing_block=block, on_save=on_save)
    
#     def _move_block_up(self, index):
#         self.designer.move_block_up(index)
#         self._refresh_blocks_list()
    
#     def _move_block_down(self, index):
#         self.designer.move_block_down(index)
#         self._refresh_blocks_list()
    
#     def _delete_block(self, index):
#         self.designer.remove_block(index)
#         self._refresh_blocks_list()
    
#     def _clear_all_blocks(self):
#         if self.designer.blocks:
#             if messagebox.askyesno("Confirmer", "Supprimer tous les blocs ?"):
#                 self.designer.clear()
#                 self._refresh_blocks_list()
    
#     def _refresh_blocks_list(self):
#         """Rafraîchit la liste des blocs."""
#         for w in self.blocks_list_frame.winfo_children():
#             w.destroy()
        
#         if not self.designer.blocks:
#             self.empty_blocks_label = ctk.CTkLabel(self.blocks_list_frame, 
#                 text="Aucun bloc ajouté\nCliquez sur les boutons à gauche pour ajouter des éléments",
#                 text_color="#888", font=("Helvetica", 11))
#             self.empty_blocks_label.pack(pady=50)
#             return
        
#         for i, block in enumerate(self.designer.blocks):
#             row = ctk.CTkFrame(self.blocks_list_frame, fg_color=KRYSTO_DARK, height=50)
#             row.pack(fill="x", pady=2, padx=5)
#             row.pack_propagate(False)
            
#             # Numéro
#             ctk.CTkLabel(row, text=f"{i+1}", width=30, text_color="#888",
#                 font=("Helvetica", 11, "bold")).pack(side="left", padx=8)
            
#             # Preview texte
#             preview_text = block.get_preview_text()
#             if len(preview_text) > 60:
#                 preview_text = preview_text[:60] + "..."
#             ctk.CTkLabel(row, text=preview_text, anchor="w",
#                 font=("Helvetica", 10)).pack(side="left", fill="x", expand=True, padx=5)
            
#             # Boutons actions
#             bf = ctk.CTkFrame(row, fg_color="transparent")
#             bf.pack(side="right", padx=5)
            
#             if i > 0:
#                 ctk.CTkButton(bf, text="↑", width=28, height=28, fg_color="#6c757d",
#                     command=lambda idx=i: self._move_block_up(idx)).pack(side="left", padx=2)
            
#             if i < len(self.designer.blocks) - 1:
#                 ctk.CTkButton(bf, text="↓", width=28, height=28, fg_color="#6c757d",
#                     command=lambda idx=i: self._move_block_down(idx)).pack(side="left", padx=2)
            
#             ctk.CTkButton(bf, text="✏️", width=28, height=28, fg_color=KRYSTO_PRIMARY,
#                 command=lambda idx=i: self._edit_block(idx)).pack(side="left", padx=2)
            
#             ctk.CTkButton(bf, text="🗑️", width=28, height=28, fg_color="#dc3545",
#                 command=lambda idx=i: self._delete_block(idx)).pack(side="left", padx=2)
    
#     def _update_designer_recipient_count(self, *args):
#         """Met à jour le compteur de destinataires pour l'éditeur."""
#         dtype = self.designer_dest_type.get()
#         if dtype == "Pro 🏢":
#             clients = self.db.get_clients_for_mailing("pro")
#         elif dtype == "Part. 👤":
#             clients = self.db.get_clients_for_mailing("particulier")
#         else:
#             clients = self.db.get_clients_for_mailing()
#         self.designer_count_lbl.configure(text=f"{len(clients)} destinataires")
    
#     def _get_designer_html(self):
#         """Génère le HTML de l'email avec l'éditeur visuel."""
#         # Configurer le designer
#         header_map = {"Gradient": "gradient", "Simple": "simple", "Aucun": "none"}
#         self.designer.header_style = header_map.get(self.header_style.get(), "gradient")
#         self.designer.show_footer = self.show_footer_var.get()
#         self.designer.subject = self.designer_subject.get()
        
#         return self.designer.generate_html("Jean DUPONT", "client@example.com")
    
#     def _preview_designer_email(self):
#         """Prévisualise l'email de l'éditeur dans le navigateur."""
#         if not self.designer.blocks:
#             messagebox.showwarning("Attention", "Ajoutez au moins un bloc à votre email!")
#             return
        
#         html = self._get_designer_html()
        
#         import tempfile
#         with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
#             f.write(html)
#             temp_path = f.name
        
#         webbrowser.open(f'file://{temp_path}')
#         messagebox.showinfo("Aperçu", f"Email ouvert dans le navigateur\nFichier: {temp_path}")
    
#     def _send_designer_test(self):
#         """Envoie un email de test avec l'éditeur."""
#         if not self.smtp_config.get('password'):
#             messagebox.showwarning("SMTP", "Configurez d'abord le SMTP!")
#             self._config_smtp()
#             return
        
#         if not self.designer.blocks:
#             messagebox.showwarning("Attention", "Ajoutez au moins un bloc à votre email!")
#             return
        
#         html = self._get_designer_html()
#         subject = self.designer_subject.get() or "Test Email KRYSTO"
#         to_email = self.smtp_config['username']
        
#         def send():
#             success, msg = self.email_service.send_email(to_email, f"[TEST] {subject}", html)
#             if success:
#                 messagebox.showinfo("Succès", f"Email test envoyé à {to_email}!")
#             else:
#                 messagebox.showerror("Erreur", f"Échec: {msg}")
        
#         threading.Thread(target=send, daemon=True).start()
#         messagebox.showinfo("Envoi", f"Envoi du test à {to_email}...")
    
#     def _send_designer_campaign(self):
#         """Envoie la campagne avec l'éditeur visuel."""
#         if not self.smtp_config.get('password'):
#             messagebox.showwarning("SMTP", "Configurez d'abord le SMTP!")
#             self._config_smtp()
#             return
        
#         if not self.designer.blocks:
#             messagebox.showwarning("Attention", "Ajoutez au moins un bloc à votre email!")
#             return
        
#         subject = self.designer_subject.get()
#         if not subject:
#             messagebox.showwarning("Attention", "Entrez un sujet pour l'email!")
#             return
        
#         dtype = self.designer_dest_type.get()
#         if dtype == "Pro 🏢":
#             clients = self.db.get_clients_for_mailing("pro")
#             type_label = "Pro"
#         elif dtype == "Part. 👤":
#             clients = self.db.get_clients_for_mailing("particulier")
#             type_label = "Particulier"
#         else:
#             clients = self.db.get_clients_for_mailing()
#             type_label = "Tous"
        
#         if not clients:
#             messagebox.showwarning("Attention", "Aucun destinataire trouvé!")
#             return
        
#         if not messagebox.askyesno("Confirmer", f"Envoyer à {len(clients)} destinataires ?"):
#             return
        
#         # Fenêtre de progression
#         progress_win = ctk.CTkToplevel(self)
#         progress_win.title("📤 Envoi des emails")
#         progress_win.geometry("520x350")
#         progress_win.grab_set()
        
#         ctk.CTkLabel(progress_win, text="📤 Envoi des emails en cours...", 
#             font=("Helvetica", 14, "bold")).pack(pady=15)
        
#         progress = ctk.CTkProgressBar(progress_win, width=420)
#         progress.pack(pady=10)
#         progress.set(0)
        
#         status_lbl = ctk.CTkLabel(progress_win, text="Initialisation...", font=("Helvetica", 11))
#         status_lbl.pack(pady=5)
        
#         details_frame = ctk.CTkScrollableFrame(progress_win, height=120)
#         details_frame.pack(fill="x", padx=20, pady=10)
        
#         result_lbl = ctk.CTkLabel(progress_win, text="", font=("Helvetica", 12, "bold"))
#         result_lbl.pack(pady=5)
        
#         close_btn = ctk.CTkButton(progress_win, text="Fermer", command=progress_win.destroy,
#             fg_color="#6c757d", state="disabled", width=120)
#         close_btn.pack(pady=10)
        
#         def send_campaign():
#             success_count = 0
#             failed_count = 0
            
#             header_map = {"Gradient": "gradient", "Simple": "simple", "Aucun": "none"}
#             self.designer.header_style = header_map.get(self.header_style.get(), "gradient")
#             self.designer.show_footer = self.show_footer_var.get()
#             self.designer.subject = subject
            
#             for i, client in enumerate(clients):
#                 try:
#                     # Générer HTML personnalisé
#                     html = self.designer.generate_html(client['name'], client['email'])
                    
#                     success, msg = self.email_service.send_email(client['email'], subject, html)
                    
#                     if success:
#                         success_count += 1
#                         icon = "✅"
#                         color = KRYSTO_SECONDARY
#                     else:
#                         failed_count += 1
#                         icon = "❌"
#                         color = "#E63946"
                    
#                     # Mise à jour UI
#                     progress_win.after(0, lambda p=(i+1)/len(clients): progress.set(p))
#                     progress_win.after(0, lambda t=f"{icon} {i+1}/{len(clients)}: {client['email']}": status_lbl.configure(text=t))
                    
#                     lbl = ctk.CTkLabel(details_frame, text=f"{icon} {client['email']}", 
#                         text_color=color, font=("Helvetica", 9))
#                     progress_win.after(0, lbl.pack, {"anchor": "w"})
                    
#                     import time
#                     time.sleep(0.5)
                    
#                 except Exception as e:
#                     failed_count += 1
            
#             # Fin
#             progress_win.after(0, lambda: result_lbl.configure(
#                 text=f"✅ Envoyés: {success_count} | ❌ Échecs: {failed_count}",
#                 text_color=KRYSTO_SECONDARY if failed_count == 0 else "#F77F00"))
#             progress_win.after(0, lambda: close_btn.configure(state="normal"))
            
#             # Log dans DB
#             self.db.log_email_campaign(subject, type_label, len(clients), success_count, failed_count)
        
#         threading.Thread(target=send_campaign, daemon=True).start()
    
#     def _build_templates_tab(self):
#         scroll = ctk.CTkScrollableFrame(self.t_templates)
#         scroll.pack(fill="both", expand=True)
        
#         ctk.CTkLabel(scroll, text="📑 Templates disponibles", 
#             font=("Helvetica", 14, "bold")).pack(anchor="w", padx=10, pady=10)
        
#         templates = [
#             ("📝 Email Simple", "Message personnalisé avec design KRYSTO", "simple",
#              "Idéal pour les communications générales, annonces, informations..."),
#             ("📰 Newsletter", "Format newsletter avec sections multiples", "newsletter",
#              "Parfait pour les actualités mensuelles, résumés d'activité..."),
#             ("🎁 Promotion", "Email promotionnel avec code promo mis en avant", "promo",
#              "Pour les offres spéciales, réductions, événements...")
#         ]
        
#         for title, desc, ttype, details in templates:
#             card = ctk.CTkFrame(scroll, fg_color=KRYSTO_DARK)
#             card.pack(fill="x", padx=10, pady=5)
            
#             cf = ctk.CTkFrame(card, fg_color="transparent")
#             cf.pack(fill="x", padx=15, pady=12)
            
#             ctk.CTkLabel(cf, text=title, font=("Helvetica", 13, "bold")).pack(anchor="w")
#             ctk.CTkLabel(cf, text=desc, text_color=KRYSTO_SECONDARY, font=("Helvetica", 10)).pack(anchor="w")
#             ctk.CTkLabel(cf, text=details, text_color="#888", font=("Helvetica", 9)).pack(anchor="w", pady=(5, 0))
            
#             bf = ctk.CTkFrame(cf, fg_color="transparent")
#             bf.pack(fill="x", pady=(10, 0))
            
#             ctk.CTkButton(bf, text="Utiliser ce template", width=140, fg_color=KRYSTO_PRIMARY,
#                 command=lambda t=ttype: self._use_template(t)).pack(side="left")
            
#             ctk.CTkButton(bf, text="👁️ Aperçu", width=90, fg_color="#6c757d",
#                 command=lambda t=ttype: self._preview_template(t)).pack(side="left", padx=10)
    
#     def _build_history_tab(self):
#         self.history_frame = ctk.CTkScrollableFrame(self.t_history)
#         self.history_frame.pack(fill="both", expand=True)
#         self._refresh_history()
    
#     def _refresh_history(self):
#         for w in self.history_frame.winfo_children():
#             w.destroy()
        
#         ctk.CTkLabel(self.history_frame, text="📋 Historique des campagnes",
#             font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=10)
        
#         history = self.db.get_email_history(20)
        
#         if not history:
#             ctk.CTkLabel(self.history_frame, text="Aucune campagne envoyée pour le moment", 
#                 text_color="#888").pack(pady=20)
#             return
        
#         for h in history:
#             row = ctk.CTkFrame(self.history_frame, fg_color=KRYSTO_DARK)
#             row.pack(fill="x", pady=2, padx=10)
            
#             rf = ctk.CTkFrame(row, fg_color="transparent")
#             rf.pack(fill="x", padx=10, pady=8)
            
#             date_str = h['sent_at'][:16] if h['sent_at'] else "-"
#             ctk.CTkLabel(rf, text=date_str, width=130, font=("Helvetica", 10)).pack(side="left")
            
#             type_badge = h['recipient_type'] or "Tous"
#             ctk.CTkLabel(rf, text=type_badge, width=100, text_color=KRYSTO_SECONDARY).pack(side="left")
            
#             ctk.CTkLabel(rf, text=h['subject'] or "-", width=250, anchor="w").pack(side="left", padx=5)
            
#             ctk.CTkLabel(rf, text=f"✅ {h['success_count']}", 
#                 text_color=KRYSTO_SECONDARY, width=60).pack(side="left")
            
#             if h['failed_count']:
#                 ctk.CTkLabel(rf, text=f"❌ {h['failed_count']}", 
#                     text_color="#E63946", width=60).pack(side="left")
    
#     def _config_smtp(self):
#         def on_save(config):
#             self.smtp_config = config
#             self.email_service.update_config(config)
#             self._update_smtp_status()
        
#         SMTPConfigDialog(self, on_save=on_save)
    
#     def _quick_test_smtp(self):
#         def do_test():
#             success, msg = self.email_service.test_connection()
#             if success:
#                 messagebox.showinfo("✅ Connexion OK", msg)
#             else:
#                 messagebox.showerror("❌ Erreur", msg)
        
#         threading.Thread(target=do_test, daemon=True).start()
    
#     def _update_recipient_count(self, *args):
#         dt = self.dest_type.get()
#         ctype = "pro" if "Pro" in dt else ("particulier" if "Part" in dt else None)
#         clients = self.db.get_clients_for_mailing(ctype)
#         self.count_lbl.configure(text=f"{len(clients)} destinataires")
    
#     def _get_html_content(self):
#         """Génère le HTML selon le template sélectionné."""
#         subject = self.subject.get() or f"Message de {COMPANY_NAME}"
#         tmpl = self.template_type.get()
        
#         if tmpl == "📝 Simple":
#             content = self.simple_content.get("1.0", "end-1c")
#             return get_email_template_simple(subject, content, self.show_button.get())
        
#         elif tmpl == "📰 Newsletter":
#             sections = []
#             for line in self.nl_sections.get("1.0", "end-1c").split("\n"):
#                 if "|" in line:
#                     parts = line.split("|")
#                     if len(parts) >= 3:
#                         sections.append({
#                             'icon': parts[0].strip(),
#                             'title': parts[1].strip(),
#                             'content': parts[2].strip()
#                         })
#             return get_email_template_newsletter(
#                 self.nl_title.get() or subject,
#                 self.nl_intro.get("1.0", "end-1c"),
#                 sections,
#                 self.nl_cta_text.get(),
#                 self.nl_cta_url.get()
#             )
        
#         elif tmpl == "🎁 Promo":
#             return get_email_template_promo(
#                 self.promo_title.get() or "Offre spéciale!",
#                 self.promo_text.get("1.0", "end-1c"),
#                 self.promo_code.get() or "KRYSTO",
#                 self.promo_expiry.get() or "Bientôt"
#             )
        
#         return get_email_template_simple(subject, "<p>Contenu</p>")
    
#     def _preview_in_browser(self):
#         """Ouvre l'aperçu dans le navigateur."""
#         html = self._get_html_content()
        
#         # Remplacer les variables par des exemples
#         html = html.replace("{{name}}", "Jean DUPONT")
#         html = html.replace("{{email}}", "jean.dupont@example.com")
#         html = html.replace("{{date}}", datetime.now().strftime('%d/%m/%Y'))
        
#         # Créer fichier temporaire
#         tmp_file = os.path.join(tempfile.gettempdir(), "krysto_email_preview.html")
#         with open(tmp_file, 'w', encoding='utf-8') as f:
#             f.write(html)
        
#         # Ouvrir dans le navigateur
#         webbrowser.open(f"file://{tmp_file}")
        
#         messagebox.showinfo("👁️ Aperçu ouvert", 
#             f"L'aperçu de l'email a été ouvert dans votre navigateur.\n\n"
#             f"Fichier: {tmp_file}")
    
#     def _preview_template(self, ttype):
#         """Prévisualise un template exemple."""
#         if ttype == "simple":
#             html = get_email_template_simple(
#                 "Exemple de sujet",
#                 "<p>Bonjour <strong>Jean</strong>,</p><p>Ceci est un exemple d'email simple avec le design KRYSTO.</p>",
#                 True
#             )
#         elif ttype == "newsletter":
#             html = get_email_template_newsletter(
#                 "Newsletter KRYSTO - Janvier",
#                 "Découvrez nos actualités ce mois-ci !",
#                 [
#                     {'icon': '🆕', 'title': 'Nouveautés', 'content': 'De nouveaux produits sont arrivés.'},
#                     {'icon': '♻️', 'title': 'Impact', 'content': '500kg de plastique recyclé ce mois.'},
#                     {'icon': '📅', 'title': 'Événement', 'content': 'Marché de Nouméa ce week-end.'}
#                 ],
#                 "Découvrir", f"https://{COMPANY_WEBSITE}"
#             )
#         elif ttype == "promo":
#             html = get_email_template_promo(
#                 "Offre Spéciale -20%",
#                 "Profitez de notre promotion exceptionnelle sur tous les produits recyclés !",
#                 "KRYSTO20",
#                 "31/01/2026"
#             )
#         else:
#             return
        
#         tmp_file = os.path.join(tempfile.gettempdir(), f"krysto_template_{ttype}.html")
#         with open(tmp_file, 'w', encoding='utf-8') as f:
#             f.write(html)
#         webbrowser.open(f"file://{tmp_file}")
    
#     def _send_test(self):
#         """Envoie un email de test."""
#         if not self.smtp_config.get('password'):
#             messagebox.showwarning("⚠️ SMTP non configuré", 
#                 "Le mot de passe SMTP n'est pas configuré!\n\n"
#                 "Cliquez sur 'Configurer SMTP' pour entrer vos identifiants.")
#             self._config_smtp()
#             return
        
#         subject = self.subject.get() or f"Test {COMPANY_NAME}"
#         html = self._get_html_content()
        
#         # Personnaliser avec des exemples
#         html = html.replace("{{name}}", "Test Client")
#         html = html.replace("{{email}}", self.smtp_config['username'])
#         html = html.replace("{{date}}", datetime.now().strftime('%d/%m/%Y'))
        
#         test_email = self.smtp_config['username']
        
#         def do_send():
#             success, msg = self.email_service.send_email(test_email, f"[TEST] {subject}", html)
#             if success:
#                 messagebox.showinfo("✅ Email test envoyé!", 
#                     f"Email envoyé avec succès à:\n{test_email}\n\n"
#                     "Vérifiez votre boîte de réception (et les spams).")
#             else:
#                 messagebox.showerror("❌ Échec d'envoi", f"Erreur:\n{msg}")
        
#         threading.Thread(target=do_send, daemon=True).start()
    
#     def _send_campaign(self):
#         """Envoie la campagne email."""
#         if not self.smtp_config.get('password'):
#             messagebox.showwarning("⚠️ SMTP non configuré", 
#                 "Configurez d'abord le SMTP avec votre mot de passe!")
#             self._config_smtp()
#             return
        
#         subject = self.subject.get()
#         if not subject:
#             messagebox.showwarning("Erreur", "Veuillez entrer un sujet pour l'email")
#             return
        
#         dt = self.dest_type.get()
#         ctype = "pro" if "Pro" in dt else ("particulier" if "Part" in dt else None)
#         type_label = "Pro" if ctype == "pro" else ("Particuliers" if ctype == "particulier" else "Tous")
        
#         clients = self.db.get_clients_for_mailing(ctype)
        
#         if not clients:
#             messagebox.showwarning("Aucun destinataire", 
#                 "Aucun client avec email trouvé.\n\n"
#                 "Ajoutez des clients avec leur adresse email d'abord.")
#             return
        
#         if not messagebox.askyesno("📤 Confirmer l'envoi", 
#             f"Envoyer la campagne à {len(clients)} destinataires?\n\n"
#             f"Type: {type_label}\n"
#             f"Sujet: {subject}\n\n"
#             "⚠️ Cette action est irréversible."):
#             return
        
#         html = self._get_html_content()
        
#         # Fenêtre de progression
#         progress_win = ctk.CTkToplevel(self)
#         progress_win.title("📤 Envoi en cours...")
#         progress_win.geometry("520x350")
#         progress_win.transient(self)
        
#         ctk.CTkLabel(progress_win, text="📤 Envoi des emails en cours...",
#             font=("Helvetica", 16, "bold")).pack(pady=20)
        
#         pbar = ctk.CTkProgressBar(progress_win, width=420)
#         pbar.pack(pady=10)
#         pbar.set(0)
        
#         status_lbl = ctk.CTkLabel(progress_win, text="Préparation...")
#         status_lbl.pack(pady=10)
        
#         details_frame = ctk.CTkScrollableFrame(progress_win, height=120)
#         details_frame.pack(fill="x", padx=20, pady=10)
        
#         results_lbl = ctk.CTkLabel(progress_win, text="", font=("Helvetica", 12, "bold"))
#         results_lbl.pack(pady=10)
        
#         def update_progress(i, total, email, success):
#             pbar.set(i / total)
#             icon = "✅" if success else "❌"
#             status_lbl.configure(text=f"{icon} {i}/{total}: {email}")
            
#             col = KRYSTO_SECONDARY if success else "#E63946"
#             ctk.CTkLabel(details_frame, text=f"{icon} {email}", text_color=col, 
#                 font=("Helvetica", 9)).pack(anchor="w")
#             progress_win.update()
        
#         def send_campaign():
#             recipients = [{'email': c['email'], 'name': c['name']} for c in clients]
#             results = self.email_service.send_bulk_emails(recipients, subject, html, update_progress)
            
#             # Log dans la base
#             self.db.log_email_campaign(subject, type_label, len(clients), 
#                 results['success'], results['failed'])
            
#             # Afficher résultats
#             color = KRYSTO_SECONDARY if results['failed'] == 0 else "#F77F00"
#             results_lbl.configure(
#                 text=f"✅ Envoyés: {results['success']} | ❌ Échecs: {results['failed']}",
#                 text_color=color)
            
#             ctk.CTkButton(progress_win, text="Fermer", command=progress_win.destroy,
#                 fg_color=KRYSTO_PRIMARY, width=120).pack(pady=10)
            
#             self._refresh_history()
#             self.refresh_stats()
        
#         threading.Thread(target=send_campaign, daemon=True).start()
    
#     def _use_template(self, ttype):
#         """Utilise le template sélectionné."""
#         self.tabs.set("✏️ Composer")
        
#         if ttype == "simple":
#             self.template_type.set("📝 Simple")
#             self._on_template_change("📝 Simple")
#         elif ttype == "newsletter":
#             self.template_type.set("📰 Newsletter")
#             self._on_template_change("📰 Newsletter")
#         elif ttype == "promo":
#             self.template_type.set("🎁 Promo")
#             self._on_template_change("🎁 Promo")




# # ============================================================================
# # GÉNÉRATION PDF - KRYSTO (code original)
# # ============================================================================
# class PDFGenerator:
#     def __init__(self, db):
#         self.db = db
#         os.makedirs(PDF_DIR, exist_ok=True)
    
#     def _header(self, c, width, title):
#         c.setFillColor(colors.HexColor(KRYSTO_PRIMARY))
#         c.rect(0, 780, width, 50, fill=True, stroke=False)
#         c.setFillColor(colors.HexColor(KRYSTO_SECONDARY))
#         c.rect(width-150, 780, 150, 50, fill=True, stroke=False)
#         c.setFillColor(colors.white)
#         c.setFont("Helvetica-Bold", 20)
#         c.drawString(20, 800, f"♻️ {COMPANY_NAME}")
#         c.setFont("Helvetica", 10)
#         c.drawString(20, 785, COMPANY_ADDRESS)
#         c.setFont("Helvetica-Bold", 14)
#         c.drawRightString(width - 20, 800, title)
#         c.setFillColor(colors.black)
    
#     def _footer(self, c, width):
#         c.setFont("Helvetica", 8)
#         c.setFillColor(colors.HexColor(KRYSTO_DARK))
#         c.drawString(20, 20, f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | {COMPANY_EMAIL}")
#         c.drawRightString(width - 20, 20, f"© {datetime.now().year} {COMPANY_NAME} - {CURRENCY}")
    
#     def generate_of(self, of_id):
#         if not HAS_REPORTLAB: return None
#         of = self.db.get_of(of_id)
#         if not of: return None
#         filename = os.path.join(PDF_DIR, f"OF_{of['of_number']}.pdf")
#         c = canvas.Canvas(filename, pagesize=A4)
#         width, height = A4
#         self._header(c, width, "ORDRE DE FABRICATION")
#         c.setFont("Helvetica-Bold", 24)
#         c.setFillColor(colors.HexColor(KRYSTO_PRIMARY))
#         c.drawString(20, 740, of['of_number'])
#         y = 700
#         c.setFillColor(colors.HexColor(KRYSTO_DARK))
#         c.setFont("Helvetica-Bold", 14)
#         c.drawString(20, y, f"QUANTITÉ: {of['quantity']} pièces")
#         y -= 30
#         c.setFont("Helvetica", 10)
#         for label, value in [("Produit", of['product_name']), ("Machine", of['machine_name']), ("Moule", of['mold_name']), ("Recette", of['recipe_name'])]:
#             c.drawString(20, y, f"{label}: {value or '-'}")
#             y -= 15
#         self._footer(c, width)
#         c.save()
#         return filename
    
#     def generate_product_sheet(self, pid):
#         if not HAS_REPORTLAB: return None
#         p = self.db.get_product(pid)
#         if not p: return None
#         filename = os.path.join(PDF_DIR, f"PRODUIT_{p['reference'] or p['id']}.pdf")
#         c = canvas.Canvas(filename, pagesize=A4)
#         width, height = A4
#         self._header(c, width, "FICHE PRODUIT")
#         c.setFont("Helvetica-Bold", 20)
#         c.drawString(20, 740, p['name'])
#         c.setFont("Helvetica", 12)
#         c.drawString(20, 720, f"Réf: {p['reference'] or '-'} | {p['weight_g'] or 0}g")
#         c.drawString(20, 700, f"Prix: {format_price(p['sell_price'] or 0)} | Stock: {p['stock_qty'] or 0}")
#         self._footer(c, width)
#         c.save()
#         return filename
    
#     def generate_machine_sheet(self, mid):
#         if not HAS_REPORTLAB: return None
#         m = self.db.get_machine(mid)
#         if not m: return None
#         filename = os.path.join(PDF_DIR, f"MACHINE_{m['id']}.pdf")
#         c = canvas.Canvas(filename, pagesize=A4)
#         width, height = A4
#         self._header(c, width, "FICHE MACHINE")
#         c.setFont("Helvetica-Bold", 20)
#         c.drawString(20, 740, m['name'])
#         c.setFont("Helvetica", 11)
#         c.drawString(20, 720, f"{m['brand'] or ''} {m['model'] or ''} | {m['voltage']}")
#         self._footer(c, width)
#         c.save()
#         return filename
    
#     def generate_mold_sheet(self, mid):
#         if not HAS_REPORTLAB: return None
#         m = self.db.get_mold(mid)
#         if not m: return None
#         filename = os.path.join(PDF_DIR, f"MOULE_{m['reference'] or m['id']}.pdf")
#         c = canvas.Canvas(filename, pagesize=A4)
#         width, height = A4
#         self._header(c, width, "FICHE MOULE")
#         c.setFont("Helvetica-Bold", 20)
#         c.drawString(20, 740, m['name'])
#         c.setFont("Helvetica", 11)
#         c.drawString(20, 720, f"Réf: {m['reference'] or '-'} | {m['compatible_plastics'] or '-'}")
#         self._footer(c, width)
#         c.save()
#         return filename
    
#     def generate_order_sheet(self, oid):
#         if not HAS_REPORTLAB: return None
#         o = self.db.get_order(oid)
#         if not o: return None
#         filename = os.path.join(PDF_DIR, f"CMD_{o['order_number']}.pdf")
#         c = canvas.Canvas(filename, pagesize=A4)
#         width, height = A4
#         self._header(c, width, "BON DE COMMANDE")
#         c.setFont("Helvetica-Bold", 20)
#         c.drawString(20, 740, o['order_number'])
#         c.setFont("Helvetica", 11)
#         c.drawString(20, 720, f"Client: {o['client_name'] or '-'}")
#         c.drawString(20, 700, f"Total: {format_price(o['total_amount'] or 0)}")
#         self._footer(c, width)
#         c.save()
#         return filename


# # ============================================================================
# # DIALOGUES UI (code original)
# # ============================================================================
# class ColorPickerDialog(ctk.CTkToplevel):
#     def __init__(self, parent, initial="#808080"):
#         super().__init__(parent)
#         self.title("Couleur"); self.geometry("300x380")
#         self.selected = initial; self.result = None
#         self.preview = ctk.CTkFrame(self, height=50, fg_color=initial); self.preview.pack(fill="x", padx=20, pady=15)
#         self.r, self.g, self.b = ctk.IntVar(value=int(initial[1:3], 16)), ctk.IntVar(value=int(initial[3:5], 16)), ctk.IntVar(value=int(initial[5:7], 16))
#         for lbl, var, col in [("R", self.r, "#E63946"), ("G", self.g, KRYSTO_SECONDARY), ("B", self.b, KRYSTO_PRIMARY)]:
#             f = ctk.CTkFrame(self, fg_color="transparent"); f.pack(fill="x", padx=20, pady=3)
#             ctk.CTkLabel(f, text=lbl, width=30).pack(side="left")
#             ctk.CTkSlider(f, from_=0, to=255, variable=var, command=self._update, progress_color=col).pack(side="left", fill="x", expand=True, padx=5)
#         pf = ctk.CTkFrame(self, fg_color="transparent"); pf.pack(fill="x", padx=20, pady=10)
#         for c in ["#FFFFFF", "#000000", KRYSTO_PRIMARY, KRYSTO_SECONDARY, KRYSTO_DARK, "#FFD60A", "#F77F00", "#E63946"]:
#             ctk.CTkButton(pf, text="", width=30, height=30, fg_color=c, command=lambda x=c: self._set(x)).pack(side="left", padx=2)
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=20, pady=15)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=100).pack(side="left")
#         ctk.CTkButton(bf, text="OK", command=self._ok, fg_color=KRYSTO_PRIMARY, width=100).pack(side="right")
#         self.grab_set()
#     def _update(self, _=None): self.selected = f"#{self.r.get():02x}{self.g.get():02x}{self.b.get():02x}"; self.preview.configure(fg_color=self.selected)
#     def _set(self, h): self.r.set(int(h[1:3], 16)); self.g.set(int(h[3:5], 16)); self.b.set(int(h[5:7], 16)); self._update()
#     def _ok(self): self.result = self.selected; self.destroy()


# class StockDialog(ctk.CTkToplevel):
#     def __init__(self, parent, db, color_name=None):
#         super().__init__(parent); self.title("Mouvement stock"); self.geometry("400x300"); self.db = db
#         self.colors = db.get_all_colors()
#         ctk.CTkLabel(self, text="📦 Mouvement de stock", font=("Helvetica", 16, "bold")).pack(pady=15)
#         f1 = ctk.CTkFrame(self, fg_color="transparent"); f1.pack(fill="x", padx=25, pady=8)
#         ctk.CTkLabel(f1, text="Couleur:", width=80).pack(side="left")
#         self.color_cb = ctk.CTkComboBox(f1, values=[c['name'] for c in self.colors], width=200); self.color_cb.pack(side="left", padx=5)
#         if color_name: self.color_cb.set(color_name)
#         f2 = ctk.CTkFrame(self, fg_color="transparent"); f2.pack(fill="x", padx=25, pady=8)
#         ctk.CTkLabel(f2, text="Type:", width=80).pack(side="left")
#         self.type_var = ctk.StringVar(value="entree")
#         ctk.CTkRadioButton(f2, text="➕ Entrée", variable=self.type_var, value="entree").pack(side="left", padx=5)
#         ctk.CTkRadioButton(f2, text="➖ Sortie", variable=self.type_var, value="sortie").pack(side="left", padx=10)
#         f3 = ctk.CTkFrame(self, fg_color="transparent"); f3.pack(fill="x", padx=25, pady=8)
#         ctk.CTkLabel(f3, text="Quantité:", width=80).pack(side="left")
#         self.qty = ctk.CTkEntry(f3, width=100); self.qty.pack(side="left", padx=5)
#         ctk.CTkLabel(f3, text="kg").pack(side="left")
#         f4 = ctk.CTkFrame(self, fg_color="transparent"); f4.pack(fill="x", padx=25, pady=8)
#         ctk.CTkLabel(f4, text="Raison:", width=80).pack(side="left")
#         self.reason = ctk.CTkEntry(f4, width=200, placeholder_text="Optionnel"); self.reason.pack(side="left", padx=5)
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=25, pady=15)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=100).pack(side="left")
#         ctk.CTkButton(bf, text="✅ Valider", command=self._validate, fg_color=KRYSTO_PRIMARY, width=100).pack(side="right")
#         self.grab_set()
#     def _validate(self):
#         try: q = float(self.qty.get().replace(",", "."))
#         except: messagebox.showwarning("Erreur", "Quantité invalide"); return
#         cid = next((c['id'] for c in self.colors if c['name'] == self.color_cb.get()), None)
#         if cid: self.db.add_stock_movement(cid, q, self.type_var.get(), self.reason.get()); messagebox.showinfo("OK", "Stock mis à jour!"); self.destroy()


# class MaintenanceDialog(ctk.CTkToplevel):
#     def __init__(self, parent, db, machine_id=None, mold_id=None, on_save=None):
#         super().__init__(parent); self.title("🔧 Maintenance"); self.geometry("500x400")
#         self.db, self.machine_id, self.mold_id, self.on_save = db, machine_id, mold_id, on_save
#         ctk.CTkLabel(self, text="🔧 Maintenance", font=("Helvetica", 16, "bold")).pack(pady=12)
#         form = ctk.CTkScrollableFrame(self); form.pack(fill="both", expand=True, padx=15, pady=5)
#         f1 = ctk.CTkFrame(form, fg_color="transparent"); f1.pack(fill="x", pady=4)
#         ctk.CTkLabel(f1, text="Type:", width=100).pack(side="left")
#         self.mtype = ctk.CTkComboBox(f1, values=["Nettoyage", "Graissage", "Réparation", "Révision"], width=180)
#         self.mtype.pack(side="left", padx=5); self.mtype.set("Nettoyage")
#         f2 = ctk.CTkFrame(form, fg_color="transparent"); f2.pack(fill="x", pady=4)
#         ctk.CTkLabel(f2, text="Description:", width=100).pack(side="left")
#         self.desc = ctk.CTkTextbox(f2, height=60, width=280); self.desc.pack(side="left", padx=5)
#         f3 = ctk.CTkFrame(form, fg_color="transparent"); f3.pack(fill="x", pady=4)
#         ctk.CTkLabel(f3, text=f"Coût ({CURRENCY}):", width=100).pack(side="left")
#         self.cost = ctk.CTkEntry(f3, width=100); self.cost.pack(side="left", padx=5)
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=15, pady=12)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=100).pack(side="left")
#         ctk.CTkButton(bf, text="💾 Enregistrer", command=self._save, fg_color=KRYSTO_PRIMARY, width=120).pack(side="right")
#         self.grab_set()
#     def _save(self):
#         try: cost = float(self.cost.get() or 0)
#         except: cost = 0
#         self.db.add_maintenance(self.machine_id, self.mold_id, self.mtype.get(), self.desc.get("1.0", "end-1c"), "", cost, "", None)
#         if self.on_save: self.on_save()
#         messagebox.showinfo("OK", "Maintenance enregistrée!"); self.destroy()


# class MachineDialog(ctk.CTkToplevel):
#     def __init__(self, parent, db, machine_id=None, on_save=None):
#         super().__init__(parent); self.title("Machine"); self.geometry("520x500")
#         self.db, self.machine_id, self.on_save = db, machine_id, on_save
#         ctk.CTkLabel(self, text="🏭 Machine", font=("Helvetica", 16, "bold")).pack(pady=12)
#         scroll = ctk.CTkScrollableFrame(self); scroll.pack(fill="both", expand=True, padx=15, pady=5)
#         self.entries = {}
#         for lbl, key, w in [("Nom *", "name", 200), ("Type", "type", 120), ("Marque", "brand", 150), ("Modèle", "model", 150)]:
#             f = ctk.CTkFrame(scroll, fg_color="transparent"); f.pack(fill="x", pady=3)
#             ctk.CTkLabel(f, text=lbl, width=100, anchor="w").pack(side="left")
#             if key == "type": e = ctk.CTkComboBox(f, values=["injecteuse", "broyeur", "extrudeuse"], width=w); e.set("injecteuse")
#             else: e = ctk.CTkEntry(f, width=w)
#             e.pack(side="left", padx=5); self.entries[key] = e
#         if machine_id:
#             m = db.get_machine(machine_id)
#             if m:
#                 self.entries['name'].insert(0, m['name'] or "")
#                 self.entries['type'].set(m['machine_type'] or "injecteuse")
#                 self.entries['brand'].insert(0, m['brand'] or "")
#                 self.entries['model'].insert(0, m['model'] or "")
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=15, pady=12)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=100).pack(side="left")
#         ctk.CTkButton(bf, text="💾 Sauver", command=self._save, fg_color=KRYSTO_PRIMARY, width=100).pack(side="right")
#         self.grab_set()
#     def _save(self):
#         name = self.entries['name'].get().strip()
#         if not name: messagebox.showwarning("Erreur", "Nom requis"); return
#         self.db.save_machine(name, self.entries['type'].get(), self.entries['brand'].get(), self.entries['model'].get(), machine_id=self.machine_id)
#         if self.on_save: self.on_save()
#         messagebox.showinfo("OK", "Machine sauvegardée!"); self.destroy()


# class MoldDialog(ctk.CTkToplevel):
#     def __init__(self, parent, db, mold_id=None, on_save=None):
#         super().__init__(parent); self.title("Moule"); self.geometry("520x500")
#         self.db, self.mold_id, self.on_save = db, mold_id, on_save
#         ctk.CTkLabel(self, text="🧊 Moule", font=("Helvetica", 16, "bold")).pack(pady=12)
#         scroll = ctk.CTkScrollableFrame(self); scroll.pack(fill="both", expand=True, padx=15, pady=5)
#         self.entries = {}
#         for lbl, key, w in [("Nom *", "name", 200), ("Référence", "ref", 120), ("Dimensions", "dims", 150), ("Plastiques", "plastics", 200)]:
#             f = ctk.CTkFrame(scroll, fg_color="transparent"); f.pack(fill="x", pady=3)
#             ctk.CTkLabel(f, text=lbl, width=100, anchor="w").pack(side="left")
#             e = ctk.CTkEntry(f, width=w)
#             e.pack(side="left", padx=5); self.entries[key] = e
#         if mold_id:
#             m = db.get_mold(mold_id)
#             if m:
#                 self.entries['name'].insert(0, m['name'] or "")
#                 self.entries['ref'].insert(0, m['reference'] or "")
#                 self.entries['dims'].insert(0, m['dimensions'] or "")
#                 self.entries['plastics'].insert(0, m['compatible_plastics'] or "")
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=15, pady=12)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=100).pack(side="left")
#         ctk.CTkButton(bf, text="💾 Sauver", command=self._save, fg_color=KRYSTO_PRIMARY, width=100).pack(side="right")
#         self.grab_set()
#     def _save(self):
#         name = self.entries['name'].get().strip()
#         if not name: messagebox.showwarning("Erreur", "Nom requis"); return
#         self.db.save_mold(name, self.entries['ref'].get(), self.entries['dims'].get(), plastics=self.entries['plastics'].get(), mold_id=self.mold_id)
#         if self.on_save: self.on_save()
#         messagebox.showinfo("OK", "Moule sauvegardé!"); self.destroy()


# class ProductDialog(ctk.CTkToplevel):
#     def __init__(self, parent, db, product_id=None, on_save=None):
#         super().__init__(parent); self.title("Produit"); self.geometry("520x500")
#         self.db, self.product_id, self.on_save = db, product_id, on_save
#         self.recipes = db.get_all_recipes(); self.molds = db.get_all_molds()
#         ctk.CTkLabel(self, text="📦 Produit", font=("Helvetica", 16, "bold")).pack(pady=12)
#         scroll = ctk.CTkScrollableFrame(self); scroll.pack(fill="both", expand=True, padx=15, pady=5)
#         self.entries = {}
#         for lbl, key, w in [("Nom *", "name", 200), ("Référence", "ref", 120), ("Poids (g)", "weight", 80), (f"Prix ({CURRENCY})", "price", 100)]:
#             f = ctk.CTkFrame(scroll, fg_color="transparent"); f.pack(fill="x", pady=3)
#             ctk.CTkLabel(f, text=lbl, width=100, anchor="w").pack(side="left")
#             e = ctk.CTkEntry(f, width=w)
#             e.pack(side="left", padx=5); self.entries[key] = e
#         f_recipe = ctk.CTkFrame(scroll, fg_color="transparent"); f_recipe.pack(fill="x", pady=3)
#         ctk.CTkLabel(f_recipe, text="Recette", width=100, anchor="w").pack(side="left")
#         self.recipe_cb = ctk.CTkComboBox(f_recipe, values=["Aucune"] + [r['name'] for r in self.recipes], width=200)
#         self.recipe_cb.pack(side="left", padx=5); self.recipe_cb.set("Aucune")
#         f_mold = ctk.CTkFrame(scroll, fg_color="transparent"); f_mold.pack(fill="x", pady=3)
#         ctk.CTkLabel(f_mold, text="Moule", width=100, anchor="w").pack(side="left")
#         self.mold_cb = ctk.CTkComboBox(f_mold, values=["Aucun"] + [m['name'] for m in self.molds], width=200)
#         self.mold_cb.pack(side="left", padx=5); self.mold_cb.set("Aucun")
#         if product_id:
#             p = db.get_product(product_id)
#             if p:
#                 self.entries['name'].insert(0, p['name'] or "")
#                 self.entries['ref'].insert(0, p['reference'] or "")
#                 if p['weight_g']: self.entries['weight'].insert(0, str(p['weight_g']))
#                 if p['sell_price']: self.entries['price'].insert(0, str(int(p['sell_price'])))
#                 if p['recipe_name']: self.recipe_cb.set(p['recipe_name'])
#                 if p['mold_name']: self.mold_cb.set(p['mold_name'])
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=15, pady=12)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=100).pack(side="left")
#         ctk.CTkButton(bf, text="💾 Sauver", command=self._save, fg_color=KRYSTO_PRIMARY, width=100).pack(side="right")
#         self.grab_set()
#     def _save(self):
#         name = self.entries['name'].get().strip()
#         if not name: messagebox.showwarning("Erreur", "Nom requis"); return
#         recipe_id = next((r['id'] for r in self.recipes if r['name'] == self.recipe_cb.get()), None)
#         mold_id = next((m['id'] for m in self.molds if m['name'] == self.mold_cb.get()), None)
#         try: weight = float(self.entries['weight'].get() or 0); price = float(self.entries['price'].get() or 0)
#         except: weight, price = 0, 0
#         self.db.save_product(name, self.entries['ref'].get(), "", recipe_id, mold_id, weight, price, "", 5, None, self.product_id)
#         if self.on_save: self.on_save()
#         messagebox.showinfo("OK", "Produit sauvegardé!"); self.destroy()


# class ClientDialog(ctk.CTkToplevel):
#     def __init__(self, parent, db, client_id=None, on_save=None):
#         super().__init__(parent); self.title("Client"); self.geometry("480x520")
#         self.db, self.client_id, self.on_save = db, client_id, on_save
#         ctk.CTkLabel(self, text="👤 Client", font=("Helvetica", 16, "bold")).pack(pady=12)
#         scroll = ctk.CTkScrollableFrame(self); scroll.pack(fill="both", expand=True, padx=15, pady=5)
#         f_type = ctk.CTkFrame(scroll, fg_color="transparent"); f_type.pack(fill="x", pady=6)
#         ctk.CTkLabel(f_type, text="Type:", width=85, anchor="w").pack(side="left")
#         self.is_pro = ctk.CTkSwitch(f_type, text="Professionnel", command=self._toggle_pro)
#         self.is_pro.pack(side="left", padx=5)
#         self.ridet_frame = ctk.CTkFrame(scroll, fg_color="transparent")
#         ctk.CTkLabel(self.ridet_frame, text="RIDET:", width=85, anchor="w").pack(side="left")
#         self.ridet = ctk.CTkEntry(self.ridet_frame, width=180, placeholder_text="N° RIDET"); self.ridet.pack(side="left", padx=5)
#         self.entries = {}
#         for lbl, key, w in [("Nom *", "name", 230), ("Entreprise", "company", 230), ("Email", "email", 230), ("Téléphone", "phone", 140), ("Ville", "city", 150)]:
#             f = ctk.CTkFrame(scroll, fg_color="transparent"); f.pack(fill="x", pady=4)
#             ctk.CTkLabel(f, text=lbl, width=85, anchor="w").pack(side="left")
#             e = ctk.CTkEntry(f, width=w); e.pack(side="left", padx=5); self.entries[key] = e
#         f_news = ctk.CTkFrame(scroll, fg_color="transparent"); f_news.pack(fill="x", pady=6)
#         ctk.CTkLabel(f_news, text="Newsletter:", width=85, anchor="w").pack(side="left")
#         self.newsletter = ctk.CTkSwitch(f_news, text="Inscrit")
#         self.newsletter.pack(side="left", padx=5); self.newsletter.select()
#         if client_id:
#             c = db.get_client(client_id)
#             if c:
#                 for k, e in self.entries.items():
#                     if c[k]: e.insert(0, c[k])
#                 if c['is_professional']:
#                     self.is_pro.select(); self._toggle_pro()
#                     if c['ridet']: self.ridet.insert(0, c['ridet'])
#                 if not c['newsletter_subscribed']: self.newsletter.deselect()
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=15, pady=12)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=95).pack(side="left")
#         ctk.CTkButton(bf, text="💾 Sauver", command=self._save, fg_color=KRYSTO_PRIMARY, width=95).pack(side="right")
#         self.grab_set()
#     def _toggle_pro(self):
#         if self.is_pro.get(): self.ridet_frame.pack(fill="x", pady=4, after=self.is_pro.master)
#         else: self.ridet_frame.pack_forget()
#     def _save(self):
#         if not self.entries['name'].get().strip(): messagebox.showwarning("Erreur", "Nom requis"); return
#         self.db.save_client(self.entries['name'].get(), self.entries['company'].get(), self.is_pro.get(),
#             self.ridet.get() if self.is_pro.get() else "", self.entries['email'].get(), self.entries['phone'].get(),
#             "", self.entries['city'].get(), "", self.newsletter.get(), self.client_id)
#         if self.on_save: self.on_save()
#         messagebox.showinfo("OK", "Client sauvegardé!"); self.destroy()


# class OFDialog(ctk.CTkToplevel):
#     def __init__(self, parent, db, order_id=None, on_save=None):
#         super().__init__(parent); self.title("📋 Nouvel OF"); self.geometry("550x450")
#         self.db, self.order_id, self.on_save = db, order_id, on_save
#         self.products = db.get_all_products(); self.recipes = db.get_all_recipes()
#         self.molds = db.get_all_molds(); self.machines = db.get_all_machines()
#         ctk.CTkLabel(self, text="📋 Créer un OF", font=("Helvetica", 16, "bold")).pack(pady=12)
#         scroll = ctk.CTkScrollableFrame(self); scroll.pack(fill="both", expand=True, padx=15, pady=5)
#         f1 = ctk.CTkFrame(scroll, fg_color="transparent"); f1.pack(fill="x", pady=5)
#         ctk.CTkLabel(f1, text="Produit:", width=100).pack(side="left")
#         self.product_cb = ctk.CTkComboBox(f1, values=[p['name'] for p in self.products], width=280, command=self._on_product)
#         self.product_cb.pack(side="left", padx=5)
#         f2 = ctk.CTkFrame(scroll, fg_color="transparent"); f2.pack(fill="x", pady=5)
#         ctk.CTkLabel(f2, text="Quantité:", width=100).pack(side="left")
#         self.qty = ctk.CTkEntry(f2, width=100); self.qty.pack(side="left", padx=5)
#         ctk.CTkLabel(f2, text="pièces").pack(side="left")
#         f3 = ctk.CTkFrame(scroll, fg_color="transparent"); f3.pack(fill="x", pady=5)
#         ctk.CTkLabel(f3, text="Machine:", width=100).pack(side="left")
#         self.machine_cb = ctk.CTkComboBox(f3, values=["Aucune"] + [m['name'] for m in self.machines], width=200)
#         self.machine_cb.pack(side="left", padx=5); self.machine_cb.set("Aucune")
#         f4 = ctk.CTkFrame(scroll, fg_color="transparent"); f4.pack(fill="x", pady=5)
#         ctk.CTkLabel(f4, text="Moule:", width=100).pack(side="left")
#         self.mold_cb = ctk.CTkComboBox(f4, values=["Aucun"] + [m['name'] for m in self.molds], width=200)
#         self.mold_cb.pack(side="left", padx=5); self.mold_cb.set("Aucun")
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=15, pady=12)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=100).pack(side="left")
#         ctk.CTkButton(bf, text="✅ Créer OF", command=self._save, fg_color=KRYSTO_PRIMARY, width=120).pack(side="right")
#         self.grab_set()
#     def _on_product(self, *args):
#         p = next((p for p in self.products if p['name'] == self.product_cb.get()), None)
#         if p and p['mold_id']:
#             m = next((m for m in self.molds if m['id'] == p['mold_id']), None)
#             if m: self.mold_cb.set(m['name'])
#     def _save(self):
#         try: qty = int(self.qty.get())
#         except: messagebox.showwarning("Erreur", "Quantité invalide"); return
#         product = next((p for p in self.products if p['name'] == self.product_cb.get()), None)
#         product_id = product['id'] if product else None
#         recipe_id = product['recipe_id'] if product else None
#         mold_id = next((m['id'] for m in self.molds if m['name'] == self.mold_cb.get()), None)
#         machine_id = next((m['id'] for m in self.machines if m['name'] == self.machine_cb.get()), None)
#         of_num = self.db.create_of(product_id, recipe_id, mold_id, machine_id, qty, self.order_id)
#         if self.on_save: self.on_save()
#         messagebox.showinfo("OK", f"OF créé: {of_num}"); self.destroy()


# class OrderDialog(ctk.CTkToplevel):
#     def __init__(self, parent, db, on_save=None):
#         super().__init__(parent); self.title("📝 Nouvelle commande"); self.geometry("600x550")
#         self.db, self.on_save = db, on_save
#         self.clients = db.get_all_clients(); self.products = db.get_all_products()
#         self.items = []
#         ctk.CTkLabel(self, text="📝 Nouvelle Commande", font=("Helvetica", 16, "bold")).pack(pady=12)
#         f1 = ctk.CTkFrame(self, fg_color="transparent"); f1.pack(fill="x", padx=15, pady=5)
#         ctk.CTkLabel(f1, text="Client:", width=80).pack(side="left")
#         cnames = ["--Sélectionner--"] + [f"{c['name']} {'🏢' if c['is_professional'] else '👤'}" for c in self.clients]
#         self.client_cb = ctk.CTkComboBox(f1, values=cnames, width=300); self.client_cb.pack(side="left", padx=5); self.client_cb.set("--Sélectionner--")
#         ctk.CTkLabel(self, text="Articles", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=15, pady=(10, 5))
#         f3 = ctk.CTkFrame(self, fg_color="transparent"); f3.pack(fill="x", padx=15, pady=5)
#         self.prod_cb = ctk.CTkComboBox(f3, values=[p['name'] for p in self.products], width=200); self.prod_cb.pack(side="left", padx=2)
#         self.item_qty = ctk.CTkEntry(f3, width=60, placeholder_text="Qté"); self.item_qty.pack(side="left", padx=2)
#         self.item_price = ctk.CTkEntry(f3, width=80, placeholder_text="Prix"); self.item_price.pack(side="left", padx=2)
#         ctk.CTkButton(f3, text="➕", command=self._add_item, width=40, fg_color=KRYSTO_PRIMARY).pack(side="left", padx=5)
#         self.items_frame = ctk.CTkScrollableFrame(self, height=120); self.items_frame.pack(fill="x", padx=15, pady=5)
#         self.total_lbl = ctk.CTkLabel(self, text=f"Total: 0 {CURRENCY}", font=("Helvetica", 14, "bold"), text_color=KRYSTO_SECONDARY)
#         self.total_lbl.pack(pady=5)
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=15, pady=12)
#         ctk.CTkButton(bf, text="Annuler", command=self.destroy, fg_color="#6c757d", width=100).pack(side="left")
#         ctk.CTkButton(bf, text="✅ Créer", command=self._save, fg_color=KRYSTO_PRIMARY, width=120).pack(side="right")
#         self.grab_set()
#     def _add_item(self):
#         pname = self.prod_cb.get()
#         try: qty = int(self.item_qty.get())
#         except: messagebox.showwarning("Erreur", "Qté invalide"); return
#         p = next((p for p in self.products if p['name'] == pname), None)
#         try: price = float(self.item_price.get()) if self.item_price.get() else (p['sell_price'] if p else 0)
#         except: price = 0
#         self.items.append({'product_id': p['id'] if p else None, 'product_name': pname, 'quantity': qty, 'unit_price': price})
#         self.item_qty.delete(0, "end"); self.item_price.delete(0, "end"); self._refresh_items()
#     def _refresh_items(self):
#         for w in self.items_frame.winfo_children(): w.destroy()
#         total = 0
#         for i, item in enumerate(self.items):
#             row = ctk.CTkFrame(self.items_frame, fg_color=KRYSTO_DARK); row.pack(fill="x", pady=2)
#             ctk.CTkLabel(row, text=item['product_name'], width=180).pack(side="left", padx=5, pady=3)
#             ctk.CTkLabel(row, text=f"x{item['quantity']}").pack(side="left", padx=5)
#             subtotal = item['quantity'] * item['unit_price']; total += subtotal
#             ctk.CTkLabel(row, text=format_price(subtotal), text_color=KRYSTO_SECONDARY).pack(side="left", padx=5)
#             ctk.CTkButton(row, text="✕", width=25, fg_color="#dc3545", command=lambda x=i: self._rm_item(x)).pack(side="right", padx=3, pady=2)
#         self.total_lbl.configure(text=f"Total: {format_price(total)}")
#     def _rm_item(self, idx): del self.items[idx]; self._refresh_items()
#     def _save(self):
#         if not self.items: messagebox.showwarning("Erreur", "Ajoutez au moins un article"); return
#         cname = self.client_cb.get()
#         client_id = None
#         for c in self.clients:
#             if cname.startswith(c['name']): client_id = c['id']; break
#         order_id, order_num = self.db.create_order(client_id, self.items)
#         if self.on_save: self.on_save()
#         messagebox.showinfo("OK", f"Commande créée: {order_num}"); self.destroy()




# # ============================================================================
# # FRAMES PRINCIPALES
# # ============================================================================
# class MachinesFrame(ctk.CTkFrame):
#     def __init__(self, parent, db, on_back):
#         super().__init__(parent); self.db, self.on_back = db, on_back
#         self.pdf = PDFGenerator(db) if HAS_REPORTLAB else None
#         self._init_ui(); self.refresh()
    
#     def _init_ui(self):
#         hdr = ctk.CTkFrame(self, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkButton(hdr, text="← Retour", command=self.on_back, width=90, fg_color="#6c757d").pack(side="left")
#         ctk.CTkLabel(hdr, text="🏭 Machines & Moules", font=("Helvetica", 17, "bold")).pack(side="left", padx=12)
#         ctk.CTkButton(hdr, text="🔧 Maintenance", command=lambda: MaintenanceDialog(self, self.db, on_save=self.refresh), fg_color="#F77F00", width=110).pack(side="right")
#         self.tabs = ctk.CTkTabview(self); self.tabs.pack(fill="both", expand=True, padx=20, pady=5)
#         self.t_mach = self.tabs.add("🔧 Machines"); self.t_mold = self.tabs.add("🧊 Moules")
#         mf = ctk.CTkFrame(self.t_mach, fg_color="transparent"); mf.pack(fill="x", pady=5)
#         ctk.CTkButton(mf, text="➕ Nouvelle", command=lambda: MachineDialog(self, self.db, on_save=self.refresh), fg_color=KRYSTO_PRIMARY, width=100).pack(side="left")
#         self.mach_list = ctk.CTkScrollableFrame(self.t_mach); self.mach_list.pack(fill="both", expand=True, pady=5)
#         df = ctk.CTkFrame(self.t_mold, fg_color="transparent"); df.pack(fill="x", pady=5)
#         ctk.CTkButton(df, text="➕ Nouveau", command=lambda: MoldDialog(self, self.db, on_save=self.refresh), fg_color=KRYSTO_PRIMARY, width=100).pack(side="left")
#         self.mold_list = ctk.CTkScrollableFrame(self.t_mold); self.mold_list.pack(fill="both", expand=True, pady=5)
    
#     def refresh(self):
#         for w in self.mach_list.winfo_children(): w.destroy()
#         for w in self.mold_list.winfo_children(): w.destroy()
#         icons = {"broyeur": "🔧", "injecteuse": "💉", "extrudeuse": "🧵"}
#         for m in self.db.get_all_machines():
#             row = ctk.CTkFrame(self.mach_list, fg_color=KRYSTO_DARK); row.pack(fill="x", pady=2)
#             ctk.CTkLabel(row, text=icons.get(m['machine_type'], "⚙️"), font=("Helvetica", 18)).pack(side="left", padx=10, pady=6)
#             info = ctk.CTkFrame(row, fg_color="transparent"); info.pack(side="left", fill="x", expand=True)
#             ctk.CTkLabel(info, text=f"{m['name']}", font=("Helvetica", 11, "bold")).pack(anchor="w")
#             ctk.CTkLabel(info, text=f"{m['brand'] or ''} {m['model'] or ''}", text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
#             ctk.CTkButton(row, text="✏️", width=28, fg_color="#6c757d", command=lambda x=m['id']: MachineDialog(self, self.db, x, self.refresh)).pack(side="right", padx=2, pady=4)
#             ctk.CTkButton(row, text="🗑️", width=28, fg_color="#dc3545", command=lambda x=m['id']: self._del_mach(x)).pack(side="right", padx=2, pady=4)
#         for m in self.db.get_all_molds():
#             row = ctk.CTkFrame(self.mold_list, fg_color=KRYSTO_DARK); row.pack(fill="x", pady=2)
#             ctk.CTkLabel(row, text="🧊", font=("Helvetica", 18)).pack(side="left", padx=10, pady=6)
#             info = ctk.CTkFrame(row, fg_color="transparent"); info.pack(side="left", fill="x", expand=True)
#             ctk.CTkLabel(info, text=f"{m['name']} | {m['reference'] or '-'}", font=("Helvetica", 11, "bold")).pack(anchor="w")
#             ctk.CTkLabel(info, text=f"{m['compatible_plastics'] or '-'} | {m['usage_count']} util.", text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
#             ctk.CTkButton(row, text="✏️", width=28, fg_color="#6c757d", command=lambda x=m['id']: MoldDialog(self, self.db, x, self.refresh)).pack(side="right", padx=2, pady=4)
#             ctk.CTkButton(row, text="🗑️", width=28, fg_color="#dc3545", command=lambda x=m['id']: self._del_mold(x)).pack(side="right", padx=2, pady=4)
    
#     def _del_mach(self, mid):
#         if messagebox.askyesno("Confirmer", "Supprimer?"): self.db.delete_machine(mid); self.refresh()
#     def _del_mold(self, mid):
#         if messagebox.askyesno("Confirmer", "Supprimer?"): self.db.delete_mold(mid); self.refresh()


# class ProductsFrame(ctk.CTkFrame):
#     def __init__(self, parent, db, on_back):
#         super().__init__(parent); self.db, self.on_back = db, on_back
#         self.pdf = PDFGenerator(db) if HAS_REPORTLAB else None
#         self._init_ui(); self.refresh()
    
#     def _init_ui(self):
#         hdr = ctk.CTkFrame(self, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkButton(hdr, text="← Retour", command=self.on_back, width=90, fg_color="#6c757d").pack(side="left")
#         ctk.CTkLabel(hdr, text="📦 Produits", font=("Helvetica", 17, "bold")).pack(side="left", padx=12)
#         ctk.CTkButton(hdr, text="➕ Nouveau", command=lambda: ProductDialog(self, self.db, on_save=self.refresh), fg_color=KRYSTO_PRIMARY, width=95).pack(side="right")
#         self.search = ctk.StringVar()
#         sf = ctk.CTkFrame(self, fg_color="transparent"); sf.pack(fill="x", padx=20, pady=4)
#         ctk.CTkEntry(sf, placeholder_text="🔍 Rechercher", width=175, textvariable=self.search).pack(side="left")
#         self.search.trace_add("write", lambda *a: self.refresh())
#         self.stats_frame = ctk.CTkFrame(self); self.stats_frame.pack(fill="x", padx=20, pady=4)
#         self.list_frame = ctk.CTkScrollableFrame(self); self.list_frame.pack(fill="both", expand=True, padx=20, pady=4)
    
#     def refresh(self):
#         for w in self.stats_frame.winfo_children(): w.destroy()
#         st = self.db.get_sales_stats()
#         sr = ctk.CTkFrame(self.stats_frame, fg_color="transparent"); sr.pack(fill="x", pady=4)
#         for lbl, val in [("CA Total", format_price(st['total'])), ("30 jours", format_price(st['period'])), ("Vendus", str(st['items']))]:
#             box = ctk.CTkFrame(sr, fg_color=KRYSTO_DARK); box.pack(side="left", expand=True, fill="x", padx=2)
#             ctk.CTkLabel(box, text=lbl, text_color="#888", font=("Helvetica", 10)).pack(pady=(5, 0))
#             ctk.CTkLabel(box, text=val, font=("Helvetica", 12, "bold"), text_color=KRYSTO_SECONDARY).pack(pady=(0, 5))
#         for w in self.list_frame.winfo_children(): w.destroy()
#         for p in self.db.get_all_products(self.search.get()):
#             row = ctk.CTkFrame(self.list_frame, fg_color=KRYSTO_DARK); row.pack(fill="x", pady=2)
#             ctk.CTkLabel(row, text="📦", font=("Helvetica", 13)).pack(side="left", padx=8, pady=5)
#             info = ctk.CTkFrame(row, fg_color="transparent"); info.pack(side="left", fill="x", expand=True)
#             ctk.CTkLabel(info, text=p['name'], font=("Helvetica", 11, "bold")).pack(anchor="w")
#             ctk.CTkLabel(info, text=f"Réf: {p['reference'] or '-'} | {p['weight_g'] or 0}g", text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
#             sc = "#E63946" if (p['stock_qty'] or 0) <= (p['min_stock'] or 5) else KRYSTO_SECONDARY
#             ctk.CTkLabel(row, text=f"Stock: {p['stock_qty'] or 0}", text_color=sc, font=("Helvetica", 11, "bold")).pack(side="right", padx=8)
#             ctk.CTkLabel(row, text=format_price(p['sell_price'] or 0), text_color=KRYSTO_PRIMARY).pack(side="right", padx=5)
#             ctk.CTkButton(row, text="➕", width=28, fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK, command=lambda x=p['id']: self._add_stock(x)).pack(side="right", padx=2, pady=3)
#             ctk.CTkButton(row, text="✏️", width=28, fg_color="#6c757d", command=lambda x=p['id']: ProductDialog(self, self.db, x, self.refresh)).pack(side="right", padx=2, pady=3)
#             ctk.CTkButton(row, text="🗑️", width=28, fg_color="#dc3545", command=lambda x=p['id']: self._del(x)).pack(side="right", padx=2, pady=3)
    
#     def _add_stock(self, pid):
#         q = ctk.CTkInputDialog(text="Quantité:", title="Stock").get_input()
#         if q:
#             try: self.db.add_product_stock(pid, int(q)); self.refresh()
#             except: pass
#     def _del(self, pid):
#         if messagebox.askyesno("Confirmer", "Supprimer?"): self.db.delete_product(pid); self.refresh()


# class OFFrame(ctk.CTkFrame):
#     def __init__(self, parent, db, on_back):
#         super().__init__(parent); self.db, self.on_back = db, on_back
#         self.pdf = PDFGenerator(db) if HAS_REPORTLAB else None
#         self._init_ui(); self.refresh()
    
#     def _init_ui(self):
#         hdr = ctk.CTkFrame(self, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkButton(hdr, text="← Retour", command=self.on_back, width=90, fg_color="#6c757d").pack(side="left")
#         ctk.CTkLabel(hdr, text="📋 Ordres de Fabrication", font=("Helvetica", 17, "bold")).pack(side="left", padx=12)
#         ctk.CTkButton(hdr, text="➕ Nouvel OF", command=lambda: OFDialog(self, self.db, on_save=self.refresh), fg_color=KRYSTO_PRIMARY, width=110).pack(side="right")
#         ff = ctk.CTkFrame(self, fg_color="transparent"); ff.pack(fill="x", padx=20, pady=5)
#         ctk.CTkLabel(ff, text="Statut:").pack(side="left")
#         self.status_filter = ctk.CTkSegmentedButton(ff, values=["Tous", "draft", "pending", "in_progress", "completed"], command=lambda e: self.refresh())
#         self.status_filter.pack(side="left", padx=5); self.status_filter.set("Tous")
#         self.list_frame = ctk.CTkScrollableFrame(self); self.list_frame.pack(fill="both", expand=True, padx=20, pady=5)
    
#     def refresh(self):
#         for w in self.list_frame.winfo_children(): w.destroy()
#         status = self.status_filter.get() if self.status_filter.get() != "Tous" else None
#         ofs = self.db.get_all_of(status)
#         status_colors = {'draft': '#808080', 'pending': '#F77F00', 'in_progress': KRYSTO_PRIMARY, 'completed': KRYSTO_SECONDARY, 'cancelled': '#E63946'}
#         for o in ofs:
#             row = ctk.CTkFrame(self.list_frame, fg_color=KRYSTO_DARK); row.pack(fill="x", pady=3)
#             sc = status_colors.get(o['status'], '#888')
#             ctk.CTkFrame(row, width=5, fg_color=sc).pack(side="left", fill="y")
#             main = ctk.CTkFrame(row, fg_color="transparent"); main.pack(side="left", fill="x", expand=True, padx=8, pady=6)
#             hf = ctk.CTkFrame(main, fg_color="transparent"); hf.pack(fill="x")
#             ctk.CTkLabel(hf, text=o['of_number'], font=("Helvetica", 12, "bold")).pack(side="left")
#             ctk.CTkLabel(hf, text=o['status'].upper(), text_color=sc, font=("Helvetica", 10, "bold")).pack(side="right")
#             ctk.CTkLabel(main, text=f"{o['product_name'] or '-'} | Qté: {o['quantity']}", text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
#             bf = ctk.CTkFrame(row, fg_color="transparent"); bf.pack(side="right", padx=5, pady=3)
#             if o['status'] in ('draft', 'pending'):
#                 ctk.CTkButton(bf, text="▶", width=28, fg_color=KRYSTO_PRIMARY, command=lambda x=o['id']: self._start(x)).pack(side="left", padx=2)
#             elif o['status'] == 'in_progress':
#                 ctk.CTkButton(bf, text="✓", width=28, fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK, command=lambda x=o['id']: self._complete(x)).pack(side="left", padx=2)
#             if self.pdf:
#                 ctk.CTkButton(bf, text="📄", width=28, fg_color=KRYSTO_PRIMARY, command=lambda x=o['id']: self._print(x)).pack(side="left", padx=2)
#             ctk.CTkButton(bf, text="🗑️", width=28, fg_color="#dc3545", command=lambda x=o['id']: self._del(x)).pack(side="left", padx=2)
    
#     def _start(self, oid): self.db.update_of_status(oid, 'in_progress'); self.refresh()
#     def _complete(self, oid):
#         of = self.db.get_of(oid)
#         qty = ctk.CTkInputDialog(text=f"Quantité produite (prévu: {of['quantity']}):", title="Compléter").get_input()
#         if qty:
#             try: self.db.update_of_status(oid, 'completed', int(qty)); self.refresh()
#             except: pass
#     def _del(self, oid):
#         if messagebox.askyesno("Confirmer", "Supprimer?"): self.db.delete_of(oid); self.refresh()
#     def _print(self, oid):
#         fp = self.pdf.generate_of(oid)
#         if fp: messagebox.showinfo("PDF", f"OF généré:\n{fp}")


# class OrdersFrame(ctk.CTkFrame):
#     def __init__(self, parent, db, on_back):
#         super().__init__(parent); self.db, self.on_back = db, on_back
#         self.pdf = PDFGenerator(db) if HAS_REPORTLAB else None
#         self._init_ui(); self.refresh()
    
#     def _init_ui(self):
#         hdr = ctk.CTkFrame(self, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkButton(hdr, text="← Retour", command=self.on_back, width=90, fg_color="#6c757d").pack(side="left")
#         ctk.CTkLabel(hdr, text="📝 Commandes Clients", font=("Helvetica", 17, "bold")).pack(side="left", padx=12)
#         ctk.CTkButton(hdr, text="➕ Nouvelle", command=lambda: OrderDialog(self, self.db, on_save=self.refresh), fg_color=KRYSTO_PRIMARY, width=100).pack(side="right")
#         ff = ctk.CTkFrame(self, fg_color="transparent"); ff.pack(fill="x", padx=20, pady=5)
#         ctk.CTkLabel(ff, text="Statut:").pack(side="left")
#         self.status_filter = ctk.CTkSegmentedButton(ff, values=["Tous", "pending", "confirmed", "in_production", "delivered"], command=lambda e: self.refresh())
#         self.status_filter.pack(side="left", padx=5); self.status_filter.set("Tous")
#         self.list_frame = ctk.CTkScrollableFrame(self); self.list_frame.pack(fill="both", expand=True, padx=20, pady=5)
    
#     def refresh(self):
#         for w in self.list_frame.winfo_children(): w.destroy()
#         status = self.status_filter.get() if self.status_filter.get() != "Tous" else None
#         orders = self.db.get_all_orders(status)
#         status_colors = {'pending': '#F77F00', 'confirmed': KRYSTO_PRIMARY, 'in_production': '#9B59B6', 'ready': KRYSTO_SECONDARY, 'delivered': KRYSTO_SECONDARY}
#         for o in orders:
#             row = ctk.CTkFrame(self.list_frame, fg_color=KRYSTO_DARK); row.pack(fill="x", pady=3)
#             sc = status_colors.get(o['status'], '#888')
#             ctk.CTkFrame(row, width=5, fg_color=sc).pack(side="left", fill="y")
#             main = ctk.CTkFrame(row, fg_color="transparent"); main.pack(side="left", fill="x", expand=True, padx=8, pady=6)
#             hf = ctk.CTkFrame(main, fg_color="transparent"); hf.pack(fill="x")
#             ctk.CTkLabel(hf, text=o['order_number'], font=("Helvetica", 12, "bold")).pack(side="left")
#             if o['is_professional']:
#                 ctk.CTkLabel(hf, text="🏢 PRO", text_color=KRYSTO_SECONDARY, font=("Helvetica", 9, "bold")).pack(side="left", padx=8)
#             ctk.CTkLabel(hf, text=format_price(o['total_amount'] or 0), font=("Helvetica", 11, "bold"), text_color=KRYSTO_SECONDARY).pack(side="right")
#             ctk.CTkLabel(main, text=f"{o['client_name'] or 'Sans client'}", text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
#             bf = ctk.CTkFrame(row, fg_color="transparent"); bf.pack(side="right", padx=5, pady=3)
#             if o['status'] == 'pending':
#                 ctk.CTkButton(bf, text="✓", width=28, fg_color=KRYSTO_PRIMARY, command=lambda x=o['id']: self._update_status(x, 'confirmed')).pack(side="left", padx=2)
#             elif o['status'] == 'confirmed':
#                 ctk.CTkButton(bf, text="🏭", width=28, fg_color="#9B59B6", command=lambda x=o['id']: self._update_status(x, 'in_production')).pack(side="left", padx=2)
#             elif o['status'] == 'in_production':
#                 ctk.CTkButton(bf, text="🚚", width=28, fg_color=KRYSTO_SECONDARY, text_color=KRYSTO_DARK, command=lambda x=o['id']: self._update_status(x, 'delivered')).pack(side="left", padx=2)
#             ctk.CTkButton(bf, text="🗑️", width=28, fg_color="#dc3545", command=lambda x=o['id']: self._del(x)).pack(side="left", padx=2)
    
#     def _update_status(self, oid, status): self.db.update_order_status(oid, status); self.refresh()
#     def _del(self, oid):
#         if messagebox.askyesno("Confirmer", "Supprimer?"): self.db.delete_order(oid); self.refresh()


# class ClientsFrame(ctk.CTkFrame):
#     def __init__(self, parent, db, on_back):
#         super().__init__(parent); self.db, self.on_back = db, on_back
#         self._init_ui(); self.refresh()
    
#     def _init_ui(self):
#         hdr = ctk.CTkFrame(self, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkButton(hdr, text="← Retour", command=self.on_back, width=90, fg_color="#6c757d").pack(side="left")
#         ctk.CTkLabel(hdr, text="👥 Clients", font=("Helvetica", 17, "bold")).pack(side="left", padx=12)
#         ctk.CTkButton(hdr, text="➕ Nouveau", command=lambda: ClientDialog(self, self.db, on_save=self.refresh), fg_color=KRYSTO_PRIMARY, width=95).pack(side="right")
#         ff = ctk.CTkFrame(self, fg_color="transparent"); ff.pack(fill="x", padx=20, pady=4)
#         self.search = ctk.StringVar()
#         ctk.CTkEntry(ff, placeholder_text="🔍 Rechercher", width=175, textvariable=self.search).pack(side="left")
#         self.search.trace_add("write", lambda *a: self.refresh())
#         self.type_filter = ctk.CTkSegmentedButton(ff, values=["Tous", "Pro", "Particulier"], command=lambda e: self.refresh())
#         self.type_filter.pack(side="left", padx=10); self.type_filter.set("Tous")
#         self.stats_frame = ctk.CTkFrame(self); self.stats_frame.pack(fill="x", padx=20, pady=4)
#         self.list_frame = ctk.CTkScrollableFrame(self); self.list_frame.pack(fill="both", expand=True, padx=20, pady=6)
    
#     def refresh(self):
#         for w in self.stats_frame.winfo_children(): w.destroy()
#         stats = self.db.get_client_stats()
#         sr = ctk.CTkFrame(self.stats_frame, fg_color="transparent"); sr.pack(fill="x", pady=4)
#         for lbl, val, col in [("Total", str(stats['total']), KRYSTO_PRIMARY), ("Pro 🏢", str(stats['pro']), KRYSTO_SECONDARY), ("Part. 👤", str(stats['particulier']), "#F77F00"), ("Emails", str(stats['with_email']), "#4CAF50")]:
#             box = ctk.CTkFrame(sr, fg_color=KRYSTO_DARK); box.pack(side="left", expand=True, fill="x", padx=2)
#             ctk.CTkLabel(box, text=lbl, text_color="#888", font=("Helvetica", 10)).pack(pady=(5, 0))
#             ctk.CTkLabel(box, text=val, font=("Helvetica", 12, "bold"), text_color=col).pack(pady=(0, 5))
#         for w in self.list_frame.winfo_children(): w.destroy()
#         tf = self.type_filter.get()
#         ctype = "pro" if tf == "Pro" else ("particulier" if tf == "Particulier" else None)
#         for c in self.db.get_all_clients(self.search.get(), ctype):
#             row = ctk.CTkFrame(self.list_frame, fg_color=KRYSTO_DARK); row.pack(fill="x", pady=2)
#             badge = "🏢" if c['is_professional'] else "👤"
#             badge_color = KRYSTO_SECONDARY if c['is_professional'] else "#F77F00"
#             ctk.CTkLabel(row, text=badge, font=("Helvetica", 16), text_color=badge_color).pack(side="left", padx=8, pady=5)
#             info = ctk.CTkFrame(row, fg_color="transparent"); info.pack(side="left", fill="x", expand=True)
#             name = f"{c['name']}"
#             if c['company']: name += f" ({c['company']})"
#             ctk.CTkLabel(info, text=name, font=("Helvetica", 11, "bold")).pack(anchor="w")
#             det = c['email'] or ""
#             if c['ridet']: det += f" | RIDET: {c['ridet']}"
#             ctk.CTkLabel(info, text=det.strip() or "-", text_color="#888", font=("Helvetica", 10)).pack(anchor="w")
#             ctk.CTkLabel(row, text=format_price(c['total_purchases']), font=("Helvetica", 11, "bold"), text_color=KRYSTO_SECONDARY).pack(side="right", padx=8)
#             ctk.CTkButton(row, text="✏️", width=28, fg_color=KRYSTO_PRIMARY, command=lambda x=c['id']: ClientDialog(self, self.db, x, self.refresh)).pack(side="right", padx=2, pady=3)
#             ctk.CTkButton(row, text="🗑️", width=28, fg_color="#dc3545", command=lambda x=c['id']: self._del(x)).pack(side="right", padx=2, pady=3)
    
#     def _del(self, cid):
#         if messagebox.askyesno("Confirmer", "Supprimer?"): self.db.delete_client(cid); self.refresh()


# class ColorsFrame(ctk.CTkFrame):
#     def __init__(self, parent, db, on_back):
#         super().__init__(parent); self.db, self.on_back, self.sel_hex = db, on_back, "#808080"
#         self._init_ui(); self.refresh()
    
#     def _init_ui(self):
#         hdr = ctk.CTkFrame(self, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkButton(hdr, text="← Retour", command=self.on_back, width=90, fg_color="#6c757d").pack(side="left")
#         ctk.CTkLabel(hdr, text="🎨 Couleurs & Stocks", font=("Helvetica", 17, "bold")).pack(side="left", padx=12)
#         ctk.CTkButton(hdr, text="📦 Mouvement", command=lambda: self._stock_dlg(), fg_color=KRYSTO_PRIMARY, width=110).pack(side="right")
#         self.alert_frame = ctk.CTkFrame(self, fg_color="#3d2020")
#         self.alert_lbl = ctk.CTkLabel(self.alert_frame, text="", text_color="#E63946"); self.alert_lbl.pack(pady=5)
#         af = ctk.CTkFrame(self); af.pack(fill="x", padx=20, pady=5)
#         ctk.CTkLabel(af, text="➕ Ajouter", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=4)
#         fr = ctk.CTkFrame(af, fg_color="transparent"); fr.pack(fill="x", padx=10, pady=4)
#         self.new_name = ctk.CTkEntry(fr, placeholder_text="Nom", width=105); self.new_name.pack(side="left", padx=2)
#         self.col_btn = ctk.CTkButton(fr, text="", width=30, height=30, fg_color="#808080", command=self._pick); self.col_btn.pack(side="left", padx=2)
#         self.new_type = ctk.CTkComboBox(fr, values=["HDPE", "LDPE", "PP", "PET", "PS", "ABS", "PLA", "PETG"], width=70)
#         self.new_type.pack(side="left", padx=2); self.new_type.set("HDPE")
#         self.new_stock = ctk.CTkEntry(fr, placeholder_text="Stock kg", width=60); self.new_stock.pack(side="left", padx=2)
#         self.new_price = ctk.CTkEntry(fr, placeholder_text=f"{CURRENCY}/kg", width=70); self.new_price.pack(side="left", padx=2)
#         ctk.CTkButton(fr, text="+", command=self._add, fg_color=KRYSTO_PRIMARY, width=38).pack(side="left", padx=5)
#         self.list_frame = ctk.CTkScrollableFrame(self); self.list_frame.pack(fill="both", expand=True, padx=20, pady=5)
    
#     def _pick(self):
#         d = ColorPickerDialog(self, self.sel_hex); self.wait_window(d)
#         if d.result: self.sel_hex = d.result; self.col_btn.configure(fg_color=self.sel_hex)
    
#     def _add(self):
#         name = self.new_name.get().strip()
#         if not name: messagebox.showwarning("Erreur", "Nom requis"); return
#         try: stk = float(self.new_stock.get() or 0); price = float(self.new_price.get() or 0)
#         except: stk, price = 0, 0
#         if self.db.add_color(name, self.sel_hex, self.new_type.get(), stk, price):
#             self.new_name.delete(0, "end"); self.new_stock.delete(0, "end"); self.new_price.delete(0, "end"); self.refresh()
#         else: messagebox.showwarning("Erreur", "Existe déjà")
    
#     def _stock_dlg(self): d = StockDialog(self, self.db); self.wait_window(d); self.refresh()
    
#     def refresh(self):
#         for w in self.list_frame.winfo_children(): w.destroy()
#         low = self.db.get_low_stock_colors()
#         if low: self.alert_lbl.configure(text=f"⚠️ Stock bas: {', '.join([c['name'] for c in low])}"); self.alert_frame.pack(fill="x", padx=20, pady=3)
#         else: self.alert_frame.pack_forget()
#         for c in self.db.get_all_colors():
#             row = ctk.CTkFrame(self.list_frame, fg_color=KRYSTO_DARK); row.pack(fill="x", pady=2)
#             ctk.CTkFrame(row, width=24, height=24, fg_color=c['hex_code'], corner_radius=12).pack(side="left", padx=10, pady=5)
#             ctk.CTkLabel(row, text=c['name'], width=105, anchor="w", font=("Helvetica", 11)).pack(side="left")
#             ctk.CTkLabel(row, text=c['plastic_type'] or "-", width=50).pack(side="left")
#             sc = "#E63946" if c['stock_kg'] <= c['alert_threshold'] else KRYSTO_SECONDARY
#             ctk.CTkLabel(row, text=f"{c['stock_kg']:.2f}kg", width=70, text_color=sc, font=("Helvetica", 11, "bold")).pack(side="left")
#             ctk.CTkLabel(row, text=f"{c['price_per_kg'] or 0:.0f} {CURRENCY}/kg", width=95, text_color="#888").pack(side="left")
#             ctk.CTkButton(row, text="➕", width=28, fg_color=KRYSTO_PRIMARY, command=lambda n=c['name']: self._quick_add(n)).pack(side="right", padx=3, pady=3)
#             ctk.CTkButton(row, text="🗑️", width=28, fg_color="#dc3545", command=lambda x=c['id']: self._delete(x)).pack(side="right", padx=3, pady=3)
    
#     def _quick_add(self, cn): d = StockDialog(self, self.db, cn); self.wait_window(d); self.refresh()
#     def _delete(self, cid):
#         if messagebox.askyesno("Confirmer", "Supprimer?"): self.db.delete_color(cid); self.refresh()


# class FilamentFrame(ctk.CTkFrame):
#     def __init__(self, parent, db, on_back):
#         super().__init__(parent); self.db, self.on_back = db, on_back
#         self._init_ui(); self.refresh()
    
#     def _init_ui(self):
#         hdr = ctk.CTkFrame(self, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkButton(hdr, text="← Retour", command=self.on_back, width=90, fg_color="#6c757d").pack(side="left")
#         ctk.CTkLabel(hdr, text="🧵 Production Filament", font=("Helvetica", 17, "bold")).pack(side="left", padx=12)
#         ctk.CTkButton(hdr, text="➕ Nouvelle", command=self._new, fg_color=KRYSTO_PRIMARY, width=105).pack(side="right")
#         info = ctk.CTkFrame(self, fg_color=KRYSTO_DARK); info.pack(fill="x", padx=20, pady=6)
#         ctk.CTkLabel(info, text=f"⚡ Cadence: {FILAMENT_RATE_G_H}g/h | Ø {FILAMENT_DIAMETER}mm", font=("Helvetica", 11), text_color=KRYSTO_SECONDARY).pack(pady=6)
#         self.stats_frame = ctk.CTkFrame(self); self.stats_frame.pack(fill="x", padx=20, pady=5)
#         quick = ctk.CTkFrame(self, fg_color="transparent"); quick.pack(fill="x", padx=20, pady=4)
#         ctk.CTkLabel(quick, text="Rapide:").pack(side="left")
#         for w in SPOOL_WEIGHTS:
#             t = calc_production_time(w)
#             ctk.CTkButton(quick, text=f"{w}g ({t['formatted']})", width=95, height=26, fg_color=KRYSTO_PRIMARY, command=lambda x=w: self._quick(x)).pack(side="left", padx=3)
#         self.hist = ctk.CTkScrollableFrame(self); self.hist.pack(fill="both", expand=True, padx=20, pady=5)
    
#     def _new(self): d = FilamentDialog(self, self.db); self.wait_window(d); self.refresh()
#     def _quick(self, w): d = FilamentDialog(self, self.db); d.weight.insert(0, str(w)); d._calc()
    
#     def refresh(self):
#         for w in self.stats_frame.winfo_children(): w.destroy()
#         for w in self.hist.winfo_children(): w.destroy()
#         st = self.db.get_filament_stats()
#         sr = ctk.CTkFrame(self.stats_frame, fg_color="transparent"); sr.pack(fill="x", pady=5)
#         data = [("Total", f"{st['total_g']/1000:.2f}kg"), ("Longueur", f"{st['total_length']:.0f}m"), ("Bobines", str(st['spools']))]
#         for lbl, val in data:
#             box = ctk.CTkFrame(sr, fg_color=KRYSTO_DARK); box.pack(side="left", expand=True, fill="x", padx=2)
#             ctk.CTkLabel(box, text=lbl, text_color="#888", font=("Helvetica", 10)).pack(pady=(5, 0))
#             ctk.CTkLabel(box, text=val, font=("Helvetica", 12, "bold"), text_color=KRYSTO_SECONDARY).pack(pady=(0, 5))
#         for p in self.db.get_filament_history(20):
#             row = ctk.CTkFrame(self.hist, fg_color=KRYSTO_DARK); row.pack(fill="x", pady=2)
#             ctk.CTkLabel(row, text="🧵", font=("Helvetica", 13)).pack(side="left", padx=8, pady=4)
#             dt = p['production_date'][:10] if p['production_date'] else ""
#             ctk.CTkLabel(row, text=f"{dt} | {p['color_name']} | {p['weight_g']:.0f}g | {p['length_m']:.1f}m", font=("Helvetica", 10)).pack(side="left", padx=5)


# class FilamentDialog(ctk.CTkToplevel):
#     def __init__(self, parent, db):
#         super().__init__(parent); self.title("🧵 Production Filament"); self.geometry("520x450"); self.db = db
#         self.colors = db.get_all_colors()
#         ctk.CTkLabel(self, text="🧵 Production de Filament", font=("Helvetica", 18, "bold")).pack(pady=10)
#         form = ctk.CTkFrame(self, fg_color="transparent"); form.pack(fill="x", padx=20, pady=8)
#         r1 = ctk.CTkFrame(form, fg_color="transparent"); r1.pack(fill="x", pady=4)
#         ctk.CTkLabel(r1, text="Couleur:", width=85).pack(side="left")
#         self.color_cb = ctk.CTkComboBox(r1, values=["--Choisir--"] + [c['name'] for c in self.colors], width=150); self.color_cb.pack(side="left", padx=5); self.color_cb.set("--Choisir--")
#         r2 = ctk.CTkFrame(form, fg_color="transparent"); r2.pack(fill="x", pady=4)
#         ctk.CTkLabel(r2, text="Poids:", width=85).pack(side="left")
#         self.weight = ctk.CTkEntry(r2, width=75); self.weight.pack(side="left", padx=5); self.weight.bind("<KeyRelease>", self._calc)
#         ctk.CTkLabel(r2, text="g").pack(side="left")
#         r3 = ctk.CTkFrame(form, fg_color="transparent"); r3.pack(fill="x", pady=4)
#         ctk.CTkLabel(r3, text="Qualité:", width=85).pack(side="left")
#         self.quality = ctk.CTkComboBox(r3, values=["1", "2", "3", "4", "5"], width=55); self.quality.pack(side="left"); self.quality.set("3")
#         self.results = ctk.CTkFrame(self, fg_color=KRYSTO_DARK); self.results.pack(fill="x", padx=20, pady=10)
#         ctk.CTkLabel(self.results, text="📊 Estimations", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=8, pady=4)
#         self.length_lbl = ctk.CTkLabel(self.results, text="Longueur: -- m"); self.length_lbl.pack(anchor="w", padx=12)
#         self.time_lbl = ctk.CTkLabel(self.results, text="Temps: --"); self.time_lbl.pack(anchor="w", padx=12)
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=20, pady=12)
#         ctk.CTkButton(bf, text="Fermer", command=self.destroy, fg_color="#6c757d", width=95).pack(side="left")
#         ctk.CTkButton(bf, text="✅ Enregistrer", command=self._save, fg_color=KRYSTO_PRIMARY, width=130).pack(side="right")
#         self.grab_set()
    
#     def _calc(self, *args):
#         try: w = float(self.weight.get().replace(",", "."))
#         except: return
#         length = calc_filament_length(w); time_info = calc_production_time(w)
#         self.length_lbl.configure(text=f"Longueur: {length:.1f} m")
#         self.time_lbl.configure(text=f"Temps: {time_info['formatted']}")
    
#     def _save(self):
#         try: w = float(self.weight.get().replace(",", "."))
#         except: messagebox.showwarning("Erreur", "Poids invalide"); return
#         cname = self.color_cb.get()
#         if cname == "--Choisir--": messagebox.showwarning("Erreur", "Choisissez une couleur"); return
#         color = next((c for c in self.colors if c['name'] == cname), None)
#         self.db.log_filament(color['id'] if color else None, cname, w, None, int(self.quality.get()), None)
#         messagebox.showinfo("OK", f"Production enregistrée: {w:.0f}g | {calc_filament_length(w):.1f}m"); self.destroy()


# class RecipeEditorFrame(ctk.CTkFrame):
#     def __init__(self, parent, db, on_save, recipe_id=None):
#         super().__init__(parent); self.db, self.on_save, self.recipe_id = db, on_save, recipe_id
#         self.ingredients, self.image_path = [], None
#         self._init_ui()
#         if recipe_id: self._load()
    
#     def _init_ui(self):
#         hdr = ctk.CTkFrame(self, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkLabel(hdr, text="✏️ " + ("Modifier" if self.recipe_id else "Nouvelle recette"), font=("Helvetica", 17, "bold")).pack(side="left")
#         main = ctk.CTkFrame(self, fg_color="transparent"); main.pack(fill="both", expand=True, padx=20)
#         left = ctk.CTkFrame(main, fg_color="transparent"); left.pack(side="left", fill="both", expand=True, padx=(0, 8))
#         ctk.CTkLabel(left, text="Nom *").pack(anchor="w", pady=(6, 2))
#         self.name = ctk.CTkEntry(left, height=32); self.name.pack(fill="x")
#         r1 = ctk.CTkFrame(left, fg_color="transparent"); r1.pack(fill="x", pady=6)
#         ctk.CTkLabel(r1, text="Type:").pack(side="left")
#         self.ptype = ctk.CTkComboBox(r1, values=["HDPE", "LDPE", "PP", "PET", "PS", "ABS", "PLA", "PETG"], width=80); self.ptype.pack(side="left", padx=(5, 12)); self.ptype.set("HDPE")
#         ctk.CTkLabel(r1, text="Cat:").pack(side="left")
#         cats = self.db.get_all_categories(); self.cat_map = {c['name']: c['id'] for c in cats}
#         self.cat_cb = ctk.CTkComboBox(r1, values=["Aucune"] + list(self.cat_map.keys()), width=110); self.cat_cb.pack(side="left", padx=5); self.cat_cb.set("Aucune")
#         ctk.CTkLabel(left, text="Description").pack(anchor="w", pady=(5, 2))
#         self.desc = ctk.CTkTextbox(left, height=65); self.desc.pack(fill="x")
#         right = ctk.CTkFrame(main, fg_color=KRYSTO_DARK); right.pack(side="right", fill="both", expand=True, padx=(8, 0))
#         rh = ctk.CTkFrame(right, fg_color="transparent"); rh.pack(fill="x", padx=10, pady=6)
#         ctk.CTkLabel(rh, text="🎨 Composition", font=("Helvetica", 12, "bold")).pack(side="left")
#         self.total_lbl = ctk.CTkLabel(rh, text="0%", text_color="#888"); self.total_lbl.pack(side="right")
#         self.ing_frame = ctk.CTkScrollableFrame(right, height=140); self.ing_frame.pack(fill="both", expand=True, padx=6)
#         af = ctk.CTkFrame(right, fg_color="transparent"); af.pack(fill="x", padx=10, pady=6)
#         colors = self.db.get_all_colors(); self.color_map = {c['name']: c for c in colors}
#         self.color_cb = ctk.CTkComboBox(af, values=list(self.color_map.keys()), width=115); self.color_cb.pack(side="left")
#         self.pct = ctk.CTkEntry(af, placeholder_text="%", width=50); self.pct.pack(side="left", padx=6)
#         ctk.CTkButton(af, text="+", command=self._add_ing, width=38, fg_color=KRYSTO_PRIMARY).pack(side="left")
#         self.preview = ctk.CTkFrame(right, height=26, fg_color="#333"); self.preview.pack(fill="x", padx=10, pady=(0, 8))
#         bf = ctk.CTkFrame(self, fg_color="transparent"); bf.pack(fill="x", padx=20, pady=10)
#         ctk.CTkButton(bf, text="Annuler", command=self.on_save, fg_color="#6c757d", width=95, height=32).pack(side="left")
#         ctk.CTkButton(bf, text="💾 Sauver", command=self._save, fg_color=KRYSTO_PRIMARY, width=105, height=32).pack(side="right")
    
#     def _load(self):
#         r = self.db.get_recipe(self.recipe_id)
#         if r:
#             self.name.insert(0, r['name']); self.ptype.set(r['plastic_type'] or "HDPE")
#             if r['description']: self.desc.insert("1.0", r['description'])
#             if r['category_name']: self.cat_cb.set(r['category_name'])
#             for i in self.db.get_recipe_ingredients(self.recipe_id): self.ingredients.append((i['color_id'], i['percentage']))
#             self._refresh_ings()
    
#     def _add_ing(self):
#         cname = self.color_cb.get()
#         try: pct = float(self.pct.get().replace(",", ".").replace("%", ""))
#         except: messagebox.showwarning("Erreur", "% invalide"); return
#         if pct <= 0 or cname not in self.color_map: return
#         c = self.color_map[cname]
#         self.ingredients = [(cid, p) for cid, p in self.ingredients if cid != c['id']]
#         self.ingredients.append((c['id'], pct)); self._refresh_ings(); self.pct.delete(0, "end")
    
#     def _rm_ing(self, cid): self.ingredients = [(c, p) for c, p in self.ingredients if c != cid]; self._refresh_ings()
    
#     def _refresh_ings(self):
#         for w in self.ing_frame.winfo_children(): w.destroy()
#         total = 0; cdata = {c['id']: c for c in self.db.get_all_colors()}
#         for cid, pct in self.ingredients:
#             if cid not in cdata: continue
#             c = cdata[cid]; total += pct
#             row = ctk.CTkFrame(self.ing_frame, fg_color="#2b2b2b"); row.pack(fill="x", pady=2)
#             ctk.CTkFrame(row, width=16, height=16, fg_color=c['hex_code'], corner_radius=8).pack(side="left", padx=8, pady=4)
#             ctk.CTkLabel(row, text=c['name'], width=95, anchor="w").pack(side="left")
#             ctk.CTkLabel(row, text=f"{pct}%", width=40).pack(side="left")
#             ctk.CTkButton(row, text="✕", width=22, height=22, fg_color="#dc3545", command=lambda x=cid: self._rm_ing(x)).pack(side="right", padx=5, pady=3)
#         col = KRYSTO_SECONDARY if total == 100 else ("#dc3545" if total > 100 else "#f0ad4e")
#         self.total_lbl.configure(text=f"{total}%", text_color=col); self._update_preview()
    
#     def _update_preview(self):
#         for w in self.preview.winfo_children(): w.destroy()
#         if not self.ingredients: return
#         cdata = {c['id']: c for c in self.db.get_all_colors()}; total = sum(p for _, p in self.ingredients)
#         if total == 0: return
#         for cid, pct in sorted(self.ingredients, key=lambda x: -x[1]):
#             if cid in cdata: ctk.CTkFrame(self.preview, fg_color=cdata[cid]['hex_code'], width=int(340*pct/total)).pack(side="left", fill="y")
    
#     def _save(self):
#         name = self.name.get().strip()
#         if not name: messagebox.showwarning("Erreur", "Nom requis"); return
#         if not self.ingredients: messagebox.showwarning("Erreur", "Ajoutez ingrédients"); return
#         total = sum(p for _, p in self.ingredients)
#         if total > 100: messagebox.showerror("Erreur", f"Total={total}% > 100%!"); return
#         cat_id = self.cat_map.get(self.cat_cb.get())
#         self.db.save_recipe(name, self.desc.get("1.0", "end-1c"), self.ptype.get(), self.ingredients, self.image_path, cat_id, self.recipe_id)
#         messagebox.showinfo("OK", "Sauvegardé!"); self.on_save()


# class DashboardFrame(ctk.CTkFrame):
#     def __init__(self, parent, db, on_back):
#         super().__init__(parent); self.db, self.on_back = db, on_back
#         self._init_ui()
    
#     def _init_ui(self):
#         hdr = ctk.CTkFrame(self, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkButton(hdr, text="← Retour", command=self.on_back, width=90, fg_color="#6c757d").pack(side="left")
#         ctk.CTkLabel(hdr, text=f"📊 Dashboard {COMPANY_NAME}", font=("Helvetica", 17, "bold")).pack(side="left", padx=12)
#         ctk.CTkButton(hdr, text="💾 Backup", command=self._backup, fg_color=KRYSTO_PRIMARY, width=85).pack(side="right")
#         scroll = ctk.CTkScrollableFrame(self); scroll.pack(fill="both", expand=True, padx=20, pady=4)
#         prod = self.db.get_production_stats(); sales = self.db.get_sales_stats(); fil = self.db.get_filament_stats(); cstats = self.db.get_client_stats()
#         cards = ctk.CTkFrame(scroll, fg_color="transparent"); cards.pack(fill="x", pady=4)
#         data = [("Production", f"{prod['total']:.1f}kg", KRYSTO_PRIMARY), ("CA", format_price(sales['total']), KRYSTO_SECONDARY), ("Filament", f"{fil['total_g']/1000:.2f}kg", "#9B59B6"), ("Clients", str(cstats['total']), "#F77F00")]
#         for lbl, val, col in data:
#             card = ctk.CTkFrame(cards, fg_color=KRYSTO_DARK); card.pack(side="left", expand=True, fill="x", padx=3)
#             ctk.CTkLabel(card, text=lbl, text_color="#888").pack(pady=(8, 0))
#             ctk.CTkLabel(card, text=val, font=("Helvetica", 16, "bold"), text_color=col).pack(pady=(0, 8))
        
#         # SMTP Status
#         smtp_config = load_smtp_config()
#         smtp_frame = ctk.CTkFrame(scroll, fg_color=KRYSTO_DARK)
#         smtp_frame.pack(fill="x", pady=10)
#         sf = ctk.CTkFrame(smtp_frame, fg_color="transparent"); sf.pack(fill="x", padx=15, pady=10)
#         if smtp_config.get('password'):
#             ctk.CTkLabel(sf, text="✅ SMTP configuré", text_color=KRYSTO_SECONDARY, font=("Helvetica", 12, "bold")).pack(side="left")
#             ctk.CTkLabel(sf, text=f" | {smtp_config['host']} | {smtp_config['username']}", text_color="#888", font=("Helvetica", 10)).pack(side="left")
#         else:
#             ctk.CTkLabel(sf, text="⚠️ SMTP NON CONFIGURÉ", text_color="#E63946", font=("Helvetica", 12, "bold")).pack(side="left")
#             ctk.CTkLabel(sf, text=" - Allez dans Mailing > Configurer SMTP", text_color="#888", font=("Helvetica", 10)).pack(side="left")
        
#         # Alertes stock
#         ctk.CTkLabel(scroll, text="⚠️ Alertes Stock", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(12, 4))
#         for f in self.db.get_stock_forecast()[:5]:
#             bg = "#3d2020" if f['alert'] else KRYSTO_DARK
#             row = ctk.CTkFrame(scroll, fg_color=bg); row.pack(fill="x", pady=2)
#             ctk.CTkFrame(row, width=16, height=16, fg_color=f['hex'], corner_radius=8).pack(side="left", padx=8, pady=4)
#             ctk.CTkLabel(row, text=f['color'], width=105, anchor="w").pack(side="left")
#             ctk.CTkLabel(row, text=f"{f['stock']:.2f}kg", width=65).pack(side="left")
#             col = "#E63946" if f['alert'] else KRYSTO_SECONDARY
#             ctk.CTkLabel(row, text=f"{f['days']}j", width=45, text_color=col, font=("Helvetica", 11, "bold")).pack(side="right", padx=8)
    
#     def _backup(self): p = self.db.backup(); messagebox.showinfo("OK", f"Sauvegardé: {p}")




# # ============================================================================
# # APPLICATION PRINCIPALE KRYSTO
# # ============================================================================
# class MainApp(ctk.CTk):
#     def __init__(self):
#         super().__init__()
#         self.title(f"♻️ {COMPANY_NAME} - Plastic Workshop Manager v5.1 ({CURRENCY})")
#         self.geometry("1450x900")
#         self.minsize(1150, 750)
#         self.db = DatabaseManager()
#         self.pdf = PDFGenerator(self.db) if HAS_REPORTLAB else None
#         os.makedirs(IMAGES_DIR, exist_ok=True)
#         os.makedirs(PDF_DIR, exist_ok=True)
#         self._init_ui()
#         self._check_smtp()
#         self.show_recipes()
    
#     def _init_ui(self):
#         # Sidebar avec style KRYSTO
#         self.sidebar = ctk.CTkFrame(self, width=175, corner_radius=0, fg_color=KRYSTO_DARK)
#         self.sidebar.pack(side="left", fill="y"); self.sidebar.pack_propagate(False)
        
#         # Logo KRYSTO
#         logo_frame = ctk.CTkFrame(self.sidebar, fg_color=KRYSTO_PRIMARY)
#         logo_frame.pack(fill="x", padx=8, pady=10)
#         ctk.CTkLabel(logo_frame, text=f"♻️ {COMPANY_NAME}", font=("Helvetica", 16, "bold"), text_color="white").pack(pady=8)
        
#         menus = [
#             ("📋 Recettes", self.show_recipes),
#             ("🎨 Couleurs", self.show_colors),
#             ("🏭 Machines", self.show_machines),
#             ("🧵 Filament", self.show_filament),
#             ("📦 Produits", self.show_products),
#             ("📋 OF", self.show_of),
#             ("📝 Commandes", self.show_orders),
#             ("👥 Clients", self.show_clients),
#             ("📧 Mailing", self.show_mailing),
#             ("📊 Dashboard", self.show_dashboard),
#         ]
#         for txt, cmd in menus:
#             ctk.CTkButton(self.sidebar, text=txt, command=cmd, fg_color="transparent", 
#                 hover_color=KRYSTO_PRIMARY, anchor="w", height=34).pack(fill="x", padx=8, pady=2)
        
#         # Alertes stock
#         self.alert_btn = ctk.CTkButton(self.sidebar, text="", fg_color="#3d2020", text_color="#E63946", 
#             command=self.show_colors, height=28)
#         self._update_alerts()
        
#         # Alerte SMTP
#         self.smtp_alert = ctk.CTkFrame(self.sidebar, fg_color="#5a3030")
#         ctk.CTkLabel(self.smtp_alert, text="⚠️ SMTP", text_color="#ff6b6b", font=("Helvetica", 9, "bold")).pack(pady=2)
#         ctk.CTkButton(self.smtp_alert, text="Configurer", fg_color="#F77F00", height=24, width=100,
#             command=self._open_smtp_config).pack(pady=(0, 5))
        
#         # Status
#         status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
#         status_frame.pack(side="bottom", fill="x", padx=8, pady=5)
#         pdf_status = "📄 PDF: ✅" if HAS_REPORTLAB else "📄 PDF: ❌"
#         pdf_color = KRYSTO_SECONDARY if HAS_REPORTLAB else "#dc3545"
#         ctk.CTkLabel(status_frame, text=pdf_status, font=("Helvetica", 9), text_color=pdf_color).pack(anchor="w")
        
#         info = ctk.CTkFrame(self.sidebar, fg_color=KRYSTO_PRIMARY)
#         info.pack(side="bottom", fill="x", padx=8, pady=8)
#         ctk.CTkLabel(info, text=f"⚡ {FILAMENT_RATE_G_H}g/h | {CURRENCY}", font=("Helvetica", 10), text_color="white").pack(pady=4)
        
#         self.main = ctk.CTkFrame(self, fg_color="transparent")
#         self.main.pack(side="right", fill="both", expand=True)
    
#     def _check_smtp(self):
#         """Vérifie si le SMTP est configuré."""
#         config = load_smtp_config()
#         if config.get('password'):
#             self.smtp_alert.pack_forget()
#         else:
#             self.smtp_alert.pack(side="bottom", fill="x", padx=8, pady=5)
    
#     def _open_smtp_config(self):
#         """Ouvre la configuration SMTP."""
#         def on_save(config):
#             self._check_smtp()
#         SMTPConfigDialog(self, on_save=on_save)
    
#     def _update_alerts(self):
#         low_colors = self.db.get_low_stock_colors()
#         low_products = self.db.get_low_stock_products()
#         pending_of = len([o for o in self.db.get_all_of() if o['status'] in ('draft', 'pending')])
#         total = len(low_colors) + len(low_products)
        
#         if total or pending_of:
#             txt = f"⚠️ {total} stock" if total else ""
#             if pending_of: txt += f" | {pending_of} OF"
#             self.alert_btn.configure(text=txt.strip(" |"))
#             self.alert_btn.pack(side="bottom", fill="x", padx=8, pady=8)
#         else:
#             self.alert_btn.pack_forget()
    
#     def _clear(self):
#         for w in self.main.winfo_children(): w.destroy()
#         self._update_alerts()
#         self._check_smtp()
    
#     def show_recipes(self):
#         self._clear()
#         hdr = ctk.CTkFrame(self.main, fg_color="transparent"); hdr.pack(fill="x", padx=20, pady=10)
#         ctk.CTkLabel(hdr, text="📋 Recettes", font=("Helvetica", 19, "bold")).pack(side="left")
#         ctk.CTkButton(hdr, text="➕ Nouvelle", command=lambda: self._show_editor(), fg_color=KRYSTO_PRIMARY, width=115, height=32).pack(side="right")
        
#         ff = ctk.CTkFrame(self.main, fg_color="transparent"); ff.pack(fill="x", padx=20, pady=4)
#         self.search = ctk.StringVar()
#         ctk.CTkEntry(ff, placeholder_text="🔍 Rechercher", width=165, textvariable=self.search).pack(side="left")
#         self.search.trace_add("write", lambda *a: self._refresh_recipes())
#         ctk.CTkLabel(ff, text="Type:").pack(side="left", padx=(10, 4))
#         self.ftype = ctk.CTkComboBox(ff, values=["Tous", "HDPE", "LDPE", "PP", "PET", "PS", "ABS", "PLA", "PETG"], width=80, command=lambda e: self._refresh_recipes())
#         self.ftype.pack(side="left"); self.ftype.set("Tous")
#         cats = self.db.get_all_categories(); self.cat_map = {c['name']: c['id'] for c in cats}
#         ctk.CTkLabel(ff, text="Cat:").pack(side="left", padx=(10, 4))
#         self.fcat = ctk.CTkComboBox(ff, values=["Toutes"] + list(self.cat_map.keys()), width=105, command=lambda e: self._refresh_recipes())
#         self.fcat.pack(side="left"); self.fcat.set("Toutes")
        
#         self.rlist = ctk.CTkScrollableFrame(self.main); self.rlist.pack(fill="both", expand=True, padx=20, pady=5)
#         self._refresh_recipes()
    
#     def _refresh_recipes(self):
#         for w in self.rlist.winfo_children(): w.destroy()
#         srch = self.search.get() if hasattr(self, 'search') else ""
#         pt = self.ftype.get() if hasattr(self, 'ftype') and self.ftype.get() != "Tous" else ""
#         cn = self.fcat.get() if hasattr(self, 'fcat') else "Toutes"
#         cid = self.cat_map.get(cn) if cn != "Toutes" else None
#         recipes = self.db.get_all_recipes(srch, pt, cid)
#         if not recipes:
#             ctk.CTkLabel(self.rlist, text="Aucune recette", text_color="#888", font=("Helvetica", 14)).pack(pady=30)
#             return
#         row = None
#         for i, r in enumerate(recipes):
#             if i % 3 == 0:
#                 row = ctk.CTkFrame(self.rlist, fg_color="transparent"); row.pack(fill="x", pady=3)
#             self._make_card(row, r)
    
#     def _make_card(self, parent, r):
#         card = ctk.CTkFrame(parent, width=360, height=180, fg_color=KRYSTO_DARK); card.pack(side="left", padx=5, pady=3); card.pack_propagate(False)
#         pf = ctk.CTkFrame(card, height=50, fg_color="#2b2b2b"); pf.pack(fill="x", padx=5, pady=5); pf.pack_propagate(False)
#         ings = self.db.get_recipe_ingredients(r['id'])
#         if ings:
#             pv = ctk.CTkFrame(pf, fg_color="transparent"); pv.pack(expand=True, fill="both", padx=5, pady=10)
#             total = sum(i['percentage'] for i in ings)
#             for ing in ings:
#                 w = int(340 * (ing['percentage'] / total)) if total > 0 else 0
#                 if w > 0: ctk.CTkFrame(pv, width=w, fg_color=ing['hex_code']).pack(side="left", fill="y")
#         if r['category_name']:
#             ctk.CTkLabel(card, text=r['category_name'], fg_color=r['category_color'], corner_radius=4, font=("Helvetica", 9)).pack(anchor="w", padx=8)
#         ctk.CTkLabel(card, text=r['name'], font=("Helvetica", 12, "bold")).pack(anchor="w", padx=8, pady=(2, 0))
#         cost = self.db.get_recipe_cost(r['id'])
#         ctk.CTkLabel(card, text=f"{r['plastic_type'] or '-'} | {r['production_count']} prod. | {format_price(cost)}/kg", text_color="#888", font=("Helvetica", 10)).pack(anchor="w", padx=8)
#         bf = ctk.CTkFrame(card, fg_color="transparent"); bf.pack(fill="x", padx=5, pady=5)
#         ctk.CTkButton(bf, text="✏️", command=lambda x=r['id']: self._show_editor(x), width=34, height=26, fg_color="#6c757d").pack(side="left", padx=2)
#         ctk.CTkButton(bf, text="📋", command=lambda x=r['id']: self._dup(x), width=34, height=26, fg_color="#6c757d").pack(side="left", padx=2)
#         ctk.CTkButton(bf, text="🗑️", command=lambda x=r['id']: self._del(x), width=34, height=26, fg_color="#dc3545").pack(side="left", padx=2)
    
#     def _show_editor(self, rid=None):
#         self._clear()
#         RecipeEditorFrame(self.main, self.db, self.show_recipes, rid).pack(fill="both", expand=True)
    
#     def _dup(self, rid):
#         self.db.duplicate_recipe(rid)
#         messagebox.showinfo("OK", "Dupliquée!")
#         self.show_recipes()
    
#     def _del(self, rid):
#         if messagebox.askyesno("Confirmer", "Supprimer?"):
#             self.db.delete_recipe(rid)
#             self.show_recipes()
    
#     def show_colors(self):
#         self._clear()
#         ColorsFrame(self.main, self.db, self.show_recipes).pack(fill="both", expand=True)
    
#     def show_machines(self):
#         self._clear()
#         MachinesFrame(self.main, self.db, self.show_recipes).pack(fill="both", expand=True)
    
#     def show_filament(self):
#         self._clear()
#         FilamentFrame(self.main, self.db, self.show_recipes).pack(fill="both", expand=True)
    
#     def show_products(self):
#         self._clear()
#         ProductsFrame(self.main, self.db, self.show_recipes).pack(fill="both", expand=True)
    
#     def show_of(self):
#         self._clear()
#         OFFrame(self.main, self.db, self.show_recipes).pack(fill="both", expand=True)
    
#     def show_orders(self):
#         self._clear()
#         OrdersFrame(self.main, self.db, self.show_recipes).pack(fill="both", expand=True)
    
#     def show_clients(self):
#         self._clear()
#         ClientsFrame(self.main, self.db, self.show_recipes).pack(fill="both", expand=True)
    
#     def show_mailing(self):
#         self._clear()
#         MailingFrame(self.main, self.db, self.show_recipes).pack(fill="both", expand=True)
    
#     def show_dashboard(self):
#         self._clear()
#         DashboardFrame(self.main, self.db, self.show_recipes).pack(fill="both", expand=True)
    
#     def on_closing(self):
#         if HAS_MATPLOTLIB:
#             plt.close('all')
#         self.db.close()
#         self.destroy()


# # ============================================================================
# # POINT D'ENTRÉE
# # ============================================================================
# if __name__ == "__main__":
#     app = MainApp()
#     app.protocol("WM_DELETE_WINDOW", app.on_closing)
#     app.mainloop()
#!/usr/bin/env python3
