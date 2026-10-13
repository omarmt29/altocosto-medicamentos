"""Fuentes ya utilizadas por el comparativo (incluidos intermediarios y reserva)."""
FX_URL = "https://open.er-api.com/v6/latest/USD"
BCRD_PORTAL = "https://www.bancentral.gov.do/"
AR_DOLAR = "https://dolarapi.com/v1/dolares/oficial"
AR_BCRA = "https://www.bcra.gob.ar/"
BR_PTAX = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
)
BR_BCB = "https://www.bcb.gov.br/"
CO_TRM = "https://www.datos.gov.co/resource/32sa-8pi3.json"
CO_BANREP = "https://www.banrep.gov.co/es/estadisticas/trm"
PE_BCRP = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04646PD/json"
PE_BCRP_PORTAL = "https://www.bcrp.gob.pe/"
CL_DOLAR = "https://mindicador.cl/api/dolar"
CL_BCCH = "https://www.bcentral.cl/"
from scrapper.fx import BANXICO_TIPOS, BANXICO_PORTAL

FUENTES = {}
for codigo, pais, banco, datos, portal in (
    ("DOP", "República Dominicana", "BCRD", BCRD_PORTAL, BCRD_PORTAL),
    ("ARS", "Argentina", "BCRA (vía dolarapi.com)", AR_DOLAR, AR_BCRA),
    ("BRL", "Brasil", "Banco Central do Brasil", BR_PTAX, BR_BCB),
    ("COP", "Colombia", "Banco de la República / Superintendencia Financiera", CO_TRM, CO_BANREP),
    ("PEN", "Perú", "BCRP", PE_BCRP, PE_BCRP_PORTAL),
    ("CLP", "Chile", "BCCh (vía mindicador.cl)", CL_DOLAR, CL_BCCH),
    ("MXN", "México", "Banxico", BANXICO_TIPOS, BANXICO_PORTAL),
    ("PAB", "Panamá", "Paridad PAB/USD", "https://www.banconal.com.pa/", "https://www.banconal.com.pa/"),
):
    FUENTES[codigo] = {"moneda": codigo, "pais": pais, "banco": banco,
                       "fuente_datos_url": datos, "link": portal, "reserva_url": FX_URL}
for codigo, pais in (("CRC", "Costa Rica"), ("HNL", "Honduras"), ("GTQ", "Guatemala"),
                     ("NIO", "Nicaragua"), ("UYU", "Uruguay"), ("PYG", "Paraguay"),
                     ("GYD", "Guyana"), ("TTD", "Trinidad y Tobago"), ("BOB", "Bolivia"),
                     ("VES", "Venezuela"), ("CAD", "Canadá"), ("USD", "Estados Unidos / Ecuador")):
    FUENTES[codigo] = {"moneda": codigo, "pais": pais, "banco": None,
                       "fuente_datos_url": FX_URL, "link": FX_URL, "reserva_url": FX_URL}
