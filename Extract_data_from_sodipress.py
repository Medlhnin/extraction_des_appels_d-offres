# Extract_data_from_sodipress.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoAlertPresentException,
)
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

LOGIN_URL = "https://client.sodipress.com/Account/Login?ReturnUrl=%2F"

# ----------------------------------------------------------------------
# 1.  Création du navigateur (URL intégrée + gestion d’alertes)
# ----------------------------------------------------------------------
def get_driver() -> webdriver.Chrome:
    """Instancie Chrome, accepte automatiquement toute alerte et ouvre Sodipress."""
    opts = Options()
    opts.add_argument("--start-maximized")
    # Chrome acceptera automatiquement toute alerte non gérée
    opts.set_capability("unhandledPromptBehavior", "accept")

    driver = webdriver.Chrome(options=opts)
    driver.get(LOGIN_URL)
    return driver


def clear_datatables_alert(driver: webdriver.Chrome, timeout: int = 2) -> None:
    """
    Ferme l'alerte « DataTables warning » si elle apparaît dans les `timeout` secondes.
    Utile pour loguer les pop‑ups, bien que le comportement 'accept' les ferme déjà.
    """
    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        if "DataTables warning" in alert.text:
            print("⚠️ Alerte DataTables interceptée :", alert.text[:60], "…")
            alert.accept()  # ou .dismiss()
    except (TimeoutException, NoAlertPresentException):
        pass


# ----------------------------------------------------------------------
# 2.  Connexion
# ----------------------------------------------------------------------
def login(driver: webdriver.Chrome) -> None:
    """Se connecter à Sodipress et atteindre la liste des AO."""

    # Attendre que le champ de connexion soit présent ou lever une erreur dans un délai de 10 seconds au maximum
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "username"))
    )

    # Remplir les champs de connexion et soumettre le formulaire
    driver.find_element(By.NAME, "username").send_keys("MUNERISCONSILIA")
    driver.find_element(By.NAME, "password").send_keys("MUNERISCONSILIA1")
    driver.find_element(By.ID, "kt_login_signin_submit").click()

    WebDriverWait(driver, 10).until(EC.url_contains("client.sodipress.com"))
    print("✅ Connexion réussie")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "MesMarches"))
    )
    driver.find_element(By.ID, "MesMarches").click()

    # Lancer la recherche sans passer par la recherche avancée
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "rechercheaoG"))
        ).click()
        print("✅ Recherche lancée directement")
    except Exception as e:
        print(f"⚠️ Erreur lors du lancement de la recherche : {e}")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "card-dashed"))
    )
    print("✅ Navigation vers la page des AO réussie")


# ----------------------------------------------------------------------
# 3.  Utilitaires de nettoyage
# ----------------------------------------------------------------------
def clean_numeric_value(text: str):
    """Nettoyer et convertir une valeur numérique (Caution, Estimation)."""
    if text:
        value = re.sub(r"[^\d,.-]", "", text).replace(",", ".").strip()
        try:
            return float(value)
        except ValueError:
            return "Non spécifié"
    return "Non spécifié"


# ----------------------------------------------------------------------
# 4.  Extraction principale
# ----------------------------------------------------------------------
def extract_aos() -> pd.DataFrame:
    driver = get_driver()
    login(driver)
    clear_datatables_alert(driver)

    ao_list = []

    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        ao_cards = soup.find_all(
            "div", class_="card card-dashed card-custom gutter-b"
        )

        for ao in ao_cards:
            try:
                # 4‑a. Infos principales
                title_element = ao.find("a", class_="DetailAO")
                organization = (
                    title_element.get_text(strip=True)
                    if title_element
                    else "Non spécifié"
                )

                # 4‑b. Détails (date, type, ville)
                date_post, type_ao, city = extract_ao_details(ao)

                # 4‑c. Attributs (n° ordre, n° AO, date limite…)
                (
                    num_ordre,
                    num_ao,
                    date_limit,
                    caution,
                    estimation,
                ) = extract_ao_attributes(ao)

                # 4‑d. Description
                description = extract_ao_description(ao)

                ao_list.append(
                    [
                        organization,
                        date_post,
                        type_ao,
                        city,
                        num_ordre,
                        num_ao,
                        date_limit,
                        caution,
                        estimation,
                        description,
                    ]
                )

            except Exception as e:
                print(f"⚠️ Erreur lors de l'extraction d'un AO : {e}")

        # 4‑e. Pagination
        if not next_page(driver):
            break
        clear_datatables_alert(driver)

    driver.quit()
    return convert_to_dataframe(ao_list)


# ----------------------------------------------------------------------
# 5.  Sous‑fonctions d’extraction ponctuelle
# ----------------------------------------------------------------------
def extract_ao_details(ao):
    """Date de Poste, Type d'AO, Ville."""
    date_post, type_ao, city = ("Non spécifié",) * 3
    details_section = ao.find("div", class_="d-flex flex-wrap my-2")

    if details_section:
        details_primary = details_section.find_all(
            "a",
            class_="text-muted text-hover-primary font-weight-bold mr-lg-8 mr-5 mb-lg-0 mb-2",
        )
        details_city = details_section.find_all(
            "a", class_="text-muted text-hover-primary font-weight-bold"
        )

        for detail in details_primary:
            txt = detail.get_text(strip=True)

            if (
                re.match(r"\d{2}/\d{2}/\d{4}", txt)
                and date_post == "Non spécifié"
            ):
                date_post = txt
                continue

            if any(
                kw in txt.upper()
                for kw in ["APPEL D'OFFRES", "CONCOURS", "MARCHÉ"]
            ) and type_ao == "Non spécifié":
                type_ao = txt
                continue

        for detail in details_city:
            txt = detail.get_text(strip=True)
            if city == "Non spécifié":
                city = txt
                break

    return date_post, type_ao, city


def extract_ao_attributes(ao):
    """Numéro ordre, n° AO, date limite, caution, estimation."""
    num_ordre = "Non spécifié"  # ← valeur par défaut sécurisée
    num_ao, date_limit, caution, estimation = ("Non spécifié",) * 4

    attributes_section = ao.find_all(
        "div", class_="d-flex align-items-center flex-lg-fill mr-5 my-1"
    )

    for section in attributes_section:
        label = section.find(
            "span", class_="font-weight-bolder font-size-sm"
        )
        value = section.find_all(
            "span", class_="font-weight-bolder font-size-sm"
        )

        if not label or len(value) < 2:
            continue

        text_label = label.get_text()

        if "N°Ordre" in text_label:
            num_ordre = value[1].get_text(strip=True)
        elif "N° AO" in text_label:
            num_ao = value[1].get_text(strip=True)
        elif "Date Limite" in text_label:
            date_limit = value[1].get_text(strip=True)
        elif "Caution" in text_label:
            caution = clean_numeric_value(value[1].get_text())
        elif "Estimation" in text_label:
            estimation = clean_numeric_value(value[1].get_text())

    return num_ordre, num_ao, date_limit, caution, estimation


def extract_ao_description(ao):
    description = "Non spécifié"
    description_element = ao.find(
        "div",
        class_="flex-grow-1 font-weight-bolder font-size-h5 py-2 py-lg-2 mr-5",
    )
    if description_element:
        description = description_element.get_text(strip=True)
    return description


def next_page(driver: webdriver.Chrome) -> bool:
    """Clique sur 'Suivant' si présent, sinon termine la boucle."""
    try:
        next_button = driver.find_element(
            By.XPATH,
            "//a[contains(@onclick, 'getAoByPage') and i[contains(@class, 'ki-bold-arrow-next')]]",
        )
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(3)
        return True
    except NoSuchElementException:
        print("✅ Extraction terminée.")
        return False


# ----------------------------------------------------------------------
# 6.  Conversion finale en DataFrame
# ----------------------------------------------------------------------
def convert_to_dataframe(ao_list):
    return pd.DataFrame(
        ao_list,
        columns=[
            "Organisme",
            "Date de Poste",
            "Type d'AO",
            "Ville",
            "Numéro d'ordre",
            "Numéro AO",
            "Date Limite",
            "Caution",
            "Estimation",
            "Description",
        ],
    )
