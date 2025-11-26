import hashlib
import sys
from pathlib import Path
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit.components.v1 import html

# Garantit l'accès au module components, même si Streamlit exécute le script depuis la racine
_CURRENT_DIR = Path(__file__).resolve().parent
_CANDIDATE_DIRS = [_CURRENT_DIR, _CURRENT_DIR / "src"]
for _dir in _CANDIDATE_DIRS:
    if (_dir / "components").exists() and str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))
        break

#from components.animations import inject_animations

def _rerun_app():
    """Compatibilité Streamlit pour relancer l'app quelle que soit la version."""
    rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun_fn:
        rerun_fn()


def _set_query_params(**params):
    """Compatibilité Streamlit pour mettre à jour les query params."""
    if hasattr(st, "query_params"):
        st.query_params.clear()
        if params:
            st.query_params.update(params)
    else:
        # Fallback pour les très vieilles versions si nécessaire, ou juste pass
        pass


def inject_animations():
    """Injecte une feuille de style globale pour les animations custom."""
    if st.session_state.get("_animations_injected"):
        return
    st.session_state["_animations_injected"] = True

    st.markdown(
        """
        <style>
        .animate-fade {
            opacity: 0;
            animation: fadeIn 0.85s ease-out forwards;
        }

        .animate-slide-up {
            opacity: 0;
            transform: translateY(18px);
            animation: slideUp 0.7s ease-out forwards;
        }

        .animate-stagger > * {
            opacity: 0;
            transform: translateY(12px);
            animation: fadeInUp 0.65s ease-out forwards;
        }

        .animate-stagger > *:nth-child(1) { animation-delay: 0.05s; }
        .animate-stagger > *:nth-child(2) { animation-delay: 0.15s; }
        .animate-stagger > *:nth-child(3) { animation-delay: 0.25s; }
        .animate-stagger > *:nth-child(4) { animation-delay: 0.35s; }
        .animate-stagger > *:nth-child(5) { animation-delay: 0.45s; }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(18px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

DB_CONFIG = {
    "host": "sql12.freesqldatabase.com",
    "user": "sql12809477",
    "password": "SVFcfmAeUr",
    "database": "sql12809477",
    "port": 3306,
}

MAX_UPLOAD_BYTES = 1_000_000_000  # 1 Go
MAX_UPLOAD_MB = MAX_UPLOAD_BYTES // (1024 * 1024)


def _asset_or_remote(name: str, remote_url: str):
    """Helper pour charger une image locale ou distante"""
    p = Path(__file__).parent / "assets" / name
    return str(p) if p.exists() else remote_url


IMAGES = {
    "hero": _asset_or_remote(
        "hero_market.jpg",
        "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=2000&q=80",
    ),
    "analytics": _asset_or_remote(
        "analytics.jpg",
        "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=1600&q=80",
    ),
    "dashboard": _asset_or_remote(
        "dashboard.jpg",
        "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=1600&q=80",
    ),
    "dashboard_hero": _asset_or_remote(
        "dashboard_banner.jpg",
        "https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1600&q=80",
    ),
    "team": _asset_or_remote(
        "team.jpg",
        "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?auto=format&fit=crop&w=1600&q=80",
    ),
    "insights": _asset_or_remote(
        "insights.jpg",
        "https://images.unsplash.com/photo-1508385082359-fb06f13b8a3f?auto=format&fit=crop&w=800&q=80",
    ),
    "sales": _asset_or_remote(
        "sales.jpg",
        "https://images.unsplash.com/photo-1506617420156-8e4536971650?auto=format&fit=crop&w=2000&q=80",
    ),
    "commerce": _asset_or_remote(
        "commerce.jpg",
        "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=2000&q=80",
    ),
    "home": _asset_or_remote(
        "home.jpg",
        "https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=1600&q=80",
    ),
    "upload": _asset_or_remote(
        "upload.jpg",
        "https://images.unsplash.com/photo-1489515217757-5fd1be406fef?auto=format&fit=crop&w=1600&q=80",
    ),
    "prediction": _asset_or_remote(
        "prediction.jpg",
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1600&q=80",
    ),
    "forecast": _asset_or_remote(
        "forecast.jpg",
        "https://images.unsplash.com/photo-1517430816045-df4b7de11d1d?auto=format&fit=crop&w=1600&q=80",
    ),
}


def create_menu(show_user_menu=True):
    """Crée le menu de navigation avec le bouton de connexion"""
    menu_container = st.container()
    with menu_container:
        menu_cols = st.columns([6, 1, 1])

        with menu_cols[0]:
            st.write("")

        with menu_cols[1]:
            st.write("")
        with menu_cols[2]:
            if show_user_menu and st.session_state.get("authenticated", False):
                user_menu = st.expander(f"👤 {st.session_state.get('username', '')}")
                with user_menu:
                    st.markdown("### Menu utilisateur")
                    if "theme" not in st.session_state:
                        st.session_state.theme = "light"
                    theme_icon = "🌙" if st.session_state.theme == "light" else "☀️"
                    if st.button(
                        f"{theme_icon} Thème {st.session_state.theme.capitalize()}",
                        key="home_theme_button",
                    ):
                        st.session_state.theme = (
                            "dark" if st.session_state.theme == "light" else "light"
                        )
                    if st.button("📤 Déconnexion", key="home_logout_button"):
                        st.session_state.authenticated = False
                        st.session_state.username = ""
                        st.session_state.is_authenticated = False
                        st.session_state.user_email = ""
                        _rerun_app()

        st.divider()


def _get_connection():
    """Retourne une connexion MySQL ou lève une erreur."""
    return mysql.connector.connect(**DB_CONFIG)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_credentials(email: str, password: str):
    """Retourne l'e-mail si les identifiants sont valides."""
    connection = None
    try:
        connection = _get_connection()
        cursor = connection.cursor()
        query = "SELECT email FROM users WHERE email = %s AND password_hash = %s"
        cursor.execute(query, (email, _hash_password(password)))
        result = cursor.fetchone()
        return result[0] if result else None
    except Error as e:
        st.error(f"Erreur lors de la connexion à la base de données : {e}")
        return None
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def register_user(email: str, password: str) -> bool:
    """Crée un utilisateur. Retourne True si l'inscription réussit."""
    connection = None
    try:
        connection = _get_connection()
        cursor = connection.cursor()
        query = "INSERT INTO users (email, password_hash) VALUES (%s, %s)"
        cursor.execute(query, (email, _hash_password(password)))
        connection.commit()
        return True
    except Error as e:
        st.error(f"Erreur lors de l'inscription : {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def email_exists(email: str) -> bool:
    """Vérifie si un email existe déjà dans la base de données."""
    connection = None
    try:
        connection = _get_connection()
        cursor = connection.cursor()
        query = "SELECT email FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        return result is not None
    except Error as e:
        st.error(f"Erreur lors de la vérification de l'email : {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


def validate_password(password: str) -> tuple:
    """Valide un mot de passe. Retourne (valide, message_erreur)."""
    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    return True, ""


def validate_email(email: str) -> tuple:
    """Valide un format d'email. Retourne (valide, message_erreur)."""
    if "@" not in email or "." not in email.split("@")[1]:
        return False, "Veuillez entrer une adresse email valide."
    return True, ""


# -------------------------- Helpers dashboard dynamiques ------------------
def check_data():
    if "data" not in st.session_state:
        st.warning("⚠️ Importez d'abord un dataset depuis la section Téléversement.")
        return False
    return True


def _find_column(df, keywords):
    cols = list(df.columns)
    lowered = [c.lower() for c in cols]
    for kw in keywords:
        for idx, name in enumerate(lowered):
            if kw in name:
                return cols[idx]
    return None


def _is_date_like(series: pd.Series, sample=200):
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    try:
        values = series.dropna().astype(str)
        if values.empty:
            return False
        sample_values = values.sample(min(len(values), sample), random_state=42)
        parsed = pd.to_datetime(sample_values, errors="coerce")
        return parsed.notna().mean() > 0.6
    except Exception:
        return False


def detect_sales_columns(df: pd.DataFrame):
    df = df.copy()
    cols = df.columns
    date_col = next((c for c in cols if _is_date_like(df[c])), None)
    revenue_col = _find_column(df, ["revenue", "amount", "total", "sales", "price", "montant"])
    qty_col = _find_column(df, ["quantity", "qty", "units", "unit", "quantité", "qte"])
    product_col = _find_column(df, ["product", "item", "sku", "article", "produit"])
    store_col = _find_column(df, ["store", "shop", "branch", "location", "magasin"])
    order_col = _find_column(df, ["order_id", "order", "invoice", "transaction", "commande"])
    customer_col = _find_column(df, ["customer", "client", "buyer", "client_id"])

    if revenue_col is None and qty_col:
        price_col = _find_column(df, ["price", "unit_price", "cost", "prix"])
        if price_col:
            try:
                df["_computed_revenue"] = pd.to_numeric(df[price_col], errors="coerce") * pd.to_numeric(
                    df[qty_col], errors="coerce"
                )
                revenue_col = "_computed_revenue"
            except Exception:
                revenue_col = None

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    return {
        "df": df,
        "date_col": date_col,
        "revenue_col": revenue_col,
        "qty_col": qty_col,
        "product_col": product_col,
        "store_col": store_col,
        "order_col": order_col,
        "customer_col": customer_col,
    }


def fmt_currency(value, currency_label="GNF"):
    if value is None:
        return "N/A"
    try:
        return f"{int(value):,} {currency_label}"
    except Exception:
        return str(value)


def fmt_number(value):
    if value is None:
        return "N/A"
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value)


@st.cache_data(ttl=300)
def compute_time_series(df: pd.DataFrame, date_col: str, value_col: str, freq="D"):
    subset = df[[date_col, value_col]].dropna()
    if subset.empty:
        return pd.DataFrame()
    subset = subset.assign(date=pd.to_datetime(subset[date_col]).dt.floor(freq))
    aggregated = subset.groupby("date")[value_col].sum().reset_index().sort_values("date")
    return aggregated


# ------------ Helpers spécifiques à l'analyse produits --------------------
SEUIL_STOCK_BAS = 10
SEUIL_MARGE_CRITIQUE = 15  # pourcentage
TOP_N = 10


def check_product_data():
    if "data" not in st.session_state:
        st.warning("⚠️ Veuillez d'abord importer vos données dans la page Téléversement")
        return False
    return True


def format_currency(value):
    try:
        return f"{int(value):,} GNF"
    except Exception:
        return str(value)


def normalize_product_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {
        "product": "produit",
        "product_name": "produit",
        "item": "produit",
        "name": "produit",
        "quantity": "quantite",
        "qty": "quantite",
        "amount": "quantite",
        "price": "prix_unitaire",
        "unit_price": "prix_unitaire",
        "prix_unitaire": "prix_unitaire",
        "cost": "cout_unitaire",
        "cost_unit": "cout_unitaire",
        "unit_cost": "cout_unitaire",
        "stock": "stock",
        "inventory": "stock",
        "date": "date",
        "date_vente": "date",
        "sale_date": "date",
        "categorie": "categorie",
        "category": "categorie",
    }
    mapping = {}
    for col in df.columns:
        key = col.strip().lower().replace(" ", "_")
        if key in col_map:
            mapping[col] = col_map[key]
    if mapping:
        df = df.rename(columns=mapping)
    if "date" in df.columns:
        try:
            df["date"] = pd.to_datetime(df["date"])
        except Exception:
            pass
    return df


def calculate_product_metrics(df: pd.DataFrame):
    metrics = {}
    if all(c in df.columns for c in ["quantite", "prix_unitaire"]):
        metrics["ventes"] = df["quantite"].sum()
        metrics["ca"] = (df["quantite"] * df["prix_unitaire"]).sum()
        if "cout_unitaire" in df.columns:
            metrics["marge"] = ((df["prix_unitaire"] - df["cout_unitaire"]) * df["quantite"]).sum()
            metrics["taux_marge"] = (metrics["marge"] / metrics["ca"]) * 100 if metrics["ca"] else 0
    if "stock" in df.columns:
        metrics["stock_total"] = df["stock"].sum()
        metrics["produits_stock_bas"] = int(df[df["stock"] < SEUIL_STOCK_BAS].shape[0])
    return metrics


def render_home_page():
    inject_animations()
    st.session_state.setdefault("theme", "light")
    st.session_state.setdefault("authenticated", False)
    st.session_state["authenticated"] = st.session_state.get("is_authenticated", False)
    if st.session_state.get("user_email"):
        st.session_state["username"] = st.session_state.get("user_email", "")

    st.markdown(
        f"""
        <style>
        :root {{
            --hero-img: url('{IMAGES['hero']}');
        }}
        body, .stApp {{
            margin: 0 !important;
            padding: 0 !important;
        }}
        .main .block-container {{
            padding-top: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }}
        .block-container:first-child {{
            padding-top: 0 !important;
        }}
        .hero-section {{
            position: relative;
            margin: -10.5rem -4.25rem 0 -4.25rem;
            padding: 0;
            border-radius: 0 0 32px 32px;
            min-height: 450px;
            overflow: hidden;
            box-shadow: 0 28px 60px rgba(15, 23, 42, 0.45);
        }}
        .hero-slideshow {{
            position: absolute;
            inset: 0;
        }}
        .hero-slide {{
            position: absolute;
            inset: 0;
            background-size: cover;
            background-position: center;
            animation: heroFade 32s infinite;
            opacity: 0;
        }}
        .hero-slide-1 {{
            background-image: linear-gradient(rgba(0,0,0,0.55), rgba(0,0,0,0.55)), url('{IMAGES['hero']}');
            animation-delay: 0s;
        }}
        .hero-slide-2 {{
            background-image: linear-gradient(rgba(0,0,0,0.55), rgba(0,0,0,0.55)), url('{IMAGES['analytics']}');
            animation-delay: 8s;
        }}
        .hero-slide-3 {{
            background-image: linear-gradient(rgba(0,0,0,0.55), rgba(0,0,0,0.55)), url('{IMAGES['sales']}');
            animation-delay: 16s;
        }}
        .hero-slide-4 {{
            background-image: linear-gradient(rgba(0,0,0,0.55), rgba(0,0,0,0.55)), url('{IMAGES['commerce']}');
            animation-delay: 24s;
        }}
        .hero-content {{
            position: relative;
            z-index: 2;
            padding: 6rem 2.2rem 3rem 2.2rem;
            color: white;
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}
        @keyframes heroFade {{
            0% {{ opacity: 0; }}
            5% {{ opacity: 1; }}
            30% {{ opacity: 1; }}
            38% {{ opacity: 0; }}
            100% {{ opacity: 0; }}
        }}

        .feature-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-bottom: 2rem;
            justify-content: center;
        }}

        .feature-card {{
            background: white;
            padding: 1.75rem;
            border-radius: 16px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
            display: flex;
            flex-direction: column;
            gap: 1rem;
            border: 1px solid rgba(148, 163, 184, 0.2);
            flex: 1 1 calc(25% - 1.5rem);
            max-width: 300px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .feature-card:hover {{
            transform: translateY(-10px);
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.2);
        }}

        .feature-card img {{
            width: 100%;
            border-radius: 12px;
            object-fit: cover;
            height: 190px;
        }}

        .feature-card h3 {{
            margin: 0;
            font-size: 1.25rem;
            color: #0f172a;
        }}

        .feature-card p {{
            margin: 0;
            color: #475569;
            line-height: 1.6;
            font-size: 0.98rem;
        }}

        .advantages-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-bottom: 2rem;
            justify-content: center;
        }}

        .advantage-1 {{
            background: #e3f2fd;
            border-left: 5px solid #2196f3;
        }}

        .advantage-2 {{
            background: #e8f5e9;
            border-left: 5px solid #4caf50;
        }}

        .advantage-3 {{
            background: #fff3e0;
            border-left: 5px solid #ff9800;
        }}

        .advantage-4 {{
            background: #fce4ec;
            border-left: 5px solid #e91e63;
        }}

        .footer-block {
            margin-top: 2.5rem;
        }
        .footer-separator {
            height: 1px;
            width: 100%;
            background: linear-gradient(90deg, rgba(15,23,42,0), rgba(15,23,42,0.18), rgba(15,23,42,0));
            margin-bottom: 1.25rem;
        }
        .footer {
            text-align: center;
            color: #475569;
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    create_menu(show_user_menu=False)

    st.markdown(
        """
        <section class="hero-section animate-fade">
            <div class="hero-slideshow">
                <div class="hero-slide hero-slide-1"></div>
                <div class="hero-slide hero-slide-2"></div>
                <div class="hero-slide hero-slide-3"></div>
                <div class="hero-slide hero-slide-4"></div>
            </div>
            <div class="hero-content">
                <h1>Bienvenue sur DataVista</h1>
                <p>Votre plateforme unifiée pour analyser vos ventes et piloter la performance retail.</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    colonne1, colonne2 = st.columns(2)
    with colonne1:
        st.markdown("### Apropos")
        st.write(
            """**DataVista** est une plateforme innovante conçue pour aider les entreprises à analyser leurs données de vente, 
        identifier les tendances et prendre des décisions éclairées. Grâce à des outils avancés de visualisation et d'analyse, 
        vous pouvez optimiser vos performances et opérer les choix stratégiques."""
        )

    with colonne2:
        st.markdown("### Pourquoi nous choisir ?")
        st.write(
            """
            - **Analyse approfondie** : Explorez vos données sous différents angles pour découvrir des insights cachés.
            - **Visualisations interactives** : Des tableaux de bord dynamiques pour une prise de décision rapide.
            - **Optimisation des performances** : Identifiez les opportunités d'amélioration et maximisez vos revenus.

            Rejoignez-nous pour transformer vos données en actions concrètes et piloter votre succès !"""
        )

    if not st.session_state.get("authenticated", False):
        st.info("👋 Bienvenue sur DataVista !")

    st.markdown("## Fonctionnalités phares")
    st.markdown(
        f"""
        <section class="feature-grid animate-stagger">
            <article class="feature-card">
                <img src="{IMAGES['analytics']}" alt="Import & Analyse" loading="lazy" />
                <h3>Importation et gouvernance des données</h3>
                <p>Centralisez et nettoyez vos données pour garantir leur qualité et leur traçabilité.</p>
            </article>
            <article class="feature-card">
                <img src="{IMAGES['dashboard']}" alt="Analyse croisée" loading="lazy" />
                <h3>Analyses croisées & insights contextuels</h3>
                <p>Analysez vos performances en tenant compte des facteurs externes et segmentez vos données intelligemment.</p>
            </article>
            <article class="feature-card">
                <img src="{IMAGES['team']}" alt="Visualisations" loading="lazy" />
                <h3>Visualisation décisionnelle & reporting</h3>
                <p>Créez des tableaux de bord interactifs pour suivre vos KPIs en temps réel et partager des rapports personnalisés.</p>
            </article>
            <article class="feature-card">
                <img src="{IMAGES['forecast']}" alt="Prédictions" loading="lazy" />
                <h3>Prédictions et planification</h3>
                <p>Anticipez les tendances futures grâce à des modèles avancés et optimisez vos décisions.</p>
            </article>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## Avantages différenciants")
    st.markdown(
        """
        <section class="advantages-grid animate-stagger">
            <article class="feature-card advantage-1">
                <h3>Diagnostic 360° des performances</h3>
                <p>Consolidez vos KPIs ventes, marge et stock pour identifier rapidement les leviers de croissance.</p>
            </article>
            <article class="feature-card advantage-2">
                <h3>Segmentation dynamique</h3>
                <p>Analysez vos données par zone, magasin, catégorie ou période pour détecter les opportunités locales.</p>
            </article>
            <article class="feature-card advantage-3">
                <h3>Qualité et gouvernance des données</h3>
                <p>Assurez-vous de la fiabilité de vos analyses grâce aux contrôles, historiques d’import et alertes qualité.</p>
            </article>
            <article class="feature-card advantage-4">
                <h3>Diffusion simplifiée des insights</h3>
                <p>Partagez des tableaux de bord prêts à l’emploi et synchrones pour éclairer vos comités de décision.</p>
            </article>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    if st.session_state.get("authenticated", False):
        user_text = st.session_state.get("username", "")
    else:
        user_text = "Visiteur (connectez-vous pour accéder à toutes les fonctionnalités)"

    st.markdown(
        f"""
        <div class='footer-block'>
            <div class='footer-separator'></div>
            <div class='footer'>© 2025 DataVista · {user_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_dashboard_page():
    hero_img = IMAGES["dashboard_hero"]
    st.markdown(
        f"""
        <style>
        :root {{
            --dashboard-hero-img: url('{hero_img}');
        }}
        .dashboard-hero {{
            position: relative;
            margin: -2.5rem -2.5rem 2rem -2.5rem;
            padding: 4rem 2rem;
            border-radius: 0 0 28px 28px;
            color: white;
            backdrop-filter: blur(8px);
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 240px;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.75), rgba(15, 23, 42, 0.92)),
                        var(--dashboard-hero-img);
            background-size: cover;
            background-position: center;
            box-shadow: 0 22px 50px rgba(15, 23, 42, 0.35);
        }}
        .dashboard-hero h1 {{
            font-size: clamp(2.2rem, 4vw, 3.2rem);
            margin: 0 0 1rem 0;
            font-weight: 700;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            max-width: 1000px;
        }}
        .dashboard-hero p {{
            font-size: clamp(1.1rem, 2vw, 1.3rem);
            max-width: 800px;
            opacity: 0.95;
            line-height: 1.6;
            margin: 0 auto 1.5rem;
            text-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }}
        .dashboard-hero__meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            margin-top: 1.5rem;
        }}
        .dashboard-hero__tag {{
            background: rgba(255, 255, 255, 0.16);
            border-radius: 999px;
            padding: 0.55rem 1.25rem;
            font-size: 0.95rem;
            letter-spacing: 0.02em;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.18);
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.4rem;
            margin: 1.8rem 0 2.2rem;
        }}
        .kpi-card {{
            position: relative;
            padding: 1.8rem;
            border-radius: 18px;
            color: #fff;
            overflow: hidden;
            box-shadow: 0 20px 45px rgba(15, 23, 42, 0.25);
        }}
        .kpi-card::after {{
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.15), transparent 55%);
            pointer-events: none;
        }}
        .kpi-card__label {{
            font-size: 0.95rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            opacity: 0.85;
        }}
        .kpi-card__value {{
            font-size: 2rem;
            font-weight: 700;
            margin: 0.35rem 0 0.6rem;
        }}
        .kpi-card__caption {{
            margin: 0;
            font-size: 0.95rem;
            opacity: 0.9;
        }}
        .kpi-card--indigo {{ background: linear-gradient(135deg, #4f46e5, #312e81); }}
        .kpi-card--emerald {{ background: linear-gradient(135deg, #10b981, #047857); }}
        .kpi-card--amber {{ background: linear-gradient(135deg, #f59e0b, #b45309); }}
        .kpi-card--rose {{ background: linear-gradient(135deg, #ec4899, #9d174d); }}
        .kpi-card--sky {{ background: linear-gradient(135deg, #0ea5e9, #1e3a8a); }}
        .kpi-card--slate {{ background: linear-gradient(135deg, #475569, #111827); }}
        @media (max-width: 992px) {{
            .dashboard-hero {{
                margin: -1.5rem -1.5rem 1.5rem -1.5rem;
                padding: 3rem 1.8rem;
                border-radius: 0 0 22px 22px;
            }}
        }}
        @media (max-width: 640px) {{
            .dashboard-hero {{
                margin: -1rem -1rem 1rem -1rem;
                padding: 2.5rem 1.4rem;
            }}
        }}
        </style>
        <section class="dashboard-hero animate-fade">
            <h1>Vue d'ensemble des performances de vos ventes.</h1>
            <p>Suivez les revenus, unités vendues et tendances clés en un coup d'œil. Identifiez vos opportunités en temps réel grâce à nos indicateurs intelligents.</p>
            <div class="dashboard-hero__meta animate-stagger">
                <span class="dashboard-hero__tag">📈 KPIs en temps réel</span>
                <span class="dashboard-hero__tag">🔎 Insights automatiques</span>
                <span class="dashboard-hero__tag">📥 Exports rapides</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("📈 Dashboard Ventes — Vue professionnelle")

    if not check_data():
        return

    raw = st.session_state["data"]
    detected = detect_sales_columns(raw)
    df = detected["df"]
    date_col = detected["date_col"]
    revenue_col = detected["revenue_col"]
    qty_col = detected["qty_col"]
    product_col = detected["product_col"]
    store_col = detected["store_col"]
    order_col = detected["order_col"]
    customer_col = detected["customer_col"]

    st.sidebar.header("Paramètres affichage")
    top_n = st.sidebar.number_input("Top N (produits/magasins)", min_value=3, max_value=50, value=10, step=1)
    granularity = st.sidebar.selectbox(
        "Granularité temporelle",
        ["D", "W", "M"],
        index=0,
        format_func=lambda x: {"D": "Quotidien", "W": "Hebdo", "M": "Mensuel"}[x],
    )
    currency_label = st.sidebar.text_input("Symbole devise (optionnel)", value="€")

    n_rows, n_cols = df.shape
    global_missing_pct = round(df.isna().sum().sum() / (max(1, n_rows * n_cols)) * 100, 2)
    duplicates = int(df.duplicated().sum())

    total_revenue = None
    if revenue_col:
        total_revenue = round(pd.to_numeric(df[revenue_col], errors="coerce").sum(skipna=True))
    total_units = None
    if qty_col:
        total_units = int(pd.to_numeric(df[qty_col], errors="coerce").sum(skipna=True))
    unique_orders = int(df[order_col].nunique(dropna=True)) if order_col else None
    unique_customers = int(df[customer_col].nunique(dropna=True)) if customer_col else None
    approx_orders = unique_orders if unique_orders is not None and unique_orders > 0 else 0


def render_auth_forms():
    """Rend les formulaires de connexion et d'inscription avec validation complète."""
    st.markdown("""
    <h1 style='text-align:center; font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Arial; color:#0d3b66; margin-bottom:4px;'>Bienvenue sur DataVista</h1>
    """, unsafe_allow_html=True)
    st.markdown("""
    <p style='text-align:center; color:white; margin-top:0; margin-bottom:18px;'>Accédez à vos services — connectez-vous ou créez un compte sécurisé.</p>
    """, unsafe_allow_html=True)

    tab_connexion, tab_inscription = st.tabs(["Connexion", "Inscription"])

    # ========== TAB CONNEXION ==========
    with tab_connexion:
        st.subheader("Se connecter")
        with st.form("login_form"):
            email = st.text_input("E-mail", placeholder="Entrez votre e-mail")
            password = st.text_input("Mot de passe", type="password", placeholder="Entrez votre mot de passe")
            submitted = st.form_submit_button("Se connecter")

            if submitted:
                # Validation des champs vides
                if not email:
                    st.error("❌ L'adresse e-mail est requise.")
                elif not password:
                    st.error("❌ Le mot de passe est requis.")
                else:
                    # Validation du format email
                    is_valid_email, email_msg = validate_email(email)
                    if not is_valid_email:
                        st.error(f"❌ {email_msg}")
                    else:
                        # Vérification des identifiants
                        if verify_credentials(email, password):
                            st.success("✅ Connexion réussie !")
                            st.session_state.is_authenticated = True
                            st.session_state.user_email = email
                            st.session_state.username = email
                            _rerun_app()
                        else:
                            st.error("❌ E-mail ou mot de passe incorrect.")

    # ========== TAB INSCRIPTION ==========
    with tab_inscription:
        st.subheader("Créer un compte")
        with st.form("register_form"):
            email = st.text_input("E-mail", placeholder="Entrez votre e-mail", key="reg_email")
            password = st.text_input("Mot de passe", type="password", placeholder="Entrez votre mot de passe", key="reg_password")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password", placeholder="Confirmez votre mot de passe", key="reg_confirm")
            submitted = st.form_submit_button("S'inscrire")

            if submitted:
                # Validation des champs vides
                if not email:
                    st.error("❌ L'adresse e-mail est requise.")
                elif not password:
                    st.error("❌ Le mot de passe est requis.")
                elif not confirm_password:
                    st.error("❌ Veuillez confirmer votre mot de passe.")
                else:
                    # Validation du format email
                    is_valid_email, email_msg = validate_email(email)
                    if not is_valid_email:
                        st.error(f"❌ {email_msg}")
                    # Vérification si l'email existe déjà
                    elif email_exists(email):
                        st.error("❌ Cet e-mail est déjà utilisé. Veuillez en utiliser un autre.")
                    # Validation du mot de passe
                    else:
                        is_valid_pwd, pwd_msg = validate_password(password)
                        if not is_valid_pwd:
                            st.error(f"❌ {pwd_msg}")
                        # Vérification que les mots de passe correspondent
                        elif password != confirm_password:
                            st.error("❌ Les mots de passe ne correspondent pas.")
                        # Enregistrement du nouvel utilisateur
                        else:
                            if register_user(email, password):
                                st.success("✅ Inscription réussie ! Vous pouvez maintenant vous connecter.")
                            else:
                                st.error("❌ Une erreur s'est produite lors de l'inscription.")


def main():
    """Fonction principale."""
    st.set_page_config(page_title="Connexion - DataVista", page_icon="🔐", layout="centered")
    st.session_state.setdefault("is_authenticated", False)
    st.session_state.setdefault("user_email", "")

    if st.session_state.get("is_authenticated"):
        st.success(f"✅ Connecté en tant que {st.session_state.get('user_email', 'Utilisateur')}")
        if st.button("📤 Déconnexion"):
            st.session_state.is_authenticated = False
            st.session_state.user_email = ""
            st.session_state.username = ""
            _rerun_app()
    else:
        render_auth_forms()


if __name__ == "__main__":
    main()
