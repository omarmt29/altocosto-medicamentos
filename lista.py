"""Lista DAMAC / FOMAC con alias de busqueda por pais."""

from __future__ import annotations

MEDICAMENTOS: list[dict[str, object]] = [
    {"n": 1, "nombre": "Acetato de abiraterona", "programa": "DAMAC", "aliases": ["abiraterona", "abiraterone"]},
    {"n": 2, "nombre": "Acetato de glatiramer", "programa": "DAMAC", "aliases": ["glatiramer"]},
    {"n": 3, "nombre": "Acetato de goserelina", "programa": "DAMAC", "aliases": ["goserelina", "goserelin", "gosserrelina", "zoladex", "prozoladex"]},
    {"n": 4, "nombre": "Acetato de leuprorelina", "programa": "DAMAC", "aliases": ["leuprorelina", "leuprolide", "leuprorelin", "leuprorrelina", "lupron", "lectrum"]},
    {"n": 5, "nombre": "Ácido zoledrónico", "programa": "DAMAC", "aliases": ["zoledronico", "zoledronic", "zoledronate", "zometa", "aclasta"]},
    {"n": 6, "nombre": "Adalimumab", "programa": "DAMAC-FOMAC", "aliases": ["adalimumab", "humira", "amgevita", "hulio", "hyrimoz", "hadlima", "idacio"]},
    {"n": 7, "nombre": "Agalsidasa beta", "programa": "DAMAC", "aliases": ["agalsidasa", "agalsidase", "fabrazyme"]},
    {"n": 8, "nombre": "Atezolizumab", "programa": "DAMAC", "aliases": ["atezolizumab", "tecentriq"]},
    {"n": 9, "nombre": "Azacitidina", "programa": "DAMAC", "aliases": ["azacitidina", "azacitidine", "vidaza"]},
    {"n": 10, "nombre": "Basiliximab", "programa": "DAMAC", "aliases": ["basiliximab", "simulect"]},
    {"n": 11, "nombre": "Bendamustina", "programa": "DAMAC", "aliases": ["bendamustina", "bendamustine"]},
    {"n": 12, "nombre": "Bevacizumab", "programa": "DAMAC", "aliases": ["bevacizumab", "avastin", "mvasi", "zirabev"]},
    {"n": 13, "nombre": "Bicalutamida", "programa": "DAMAC", "aliases": ["bicalutamida", "bicalutamide", "casodex"]},
    {"n": 14, "nombre": "Bortezomib", "programa": "DAMAC", "aliases": ["bortezomib", "velcade"]},
    {"n": 15, "nombre": "Bosentán", "programa": "DAMAC", "aliases": ["bosentan", "tracleer"]},
    {"n": 16, "nombre": "Capecitabina", "programa": "DAMAC", "aliases": ["capecitabina", "capecitabine", "xeloda"]},
    {"n": 17, "nombre": "Cetuximab", "programa": "DAMAC", "aliases": ["cetuximab", "erbitux"]},
    {"n": 18, "nombre": "Ciclosporina", "programa": "DAMAC", "aliases": ["ciclosporina", "cyclosporine", "cyclosporin", "neoral", "sandimmun", "equoral"]},
    {"n": 19, "nombre": "Cladribina", "programa": "DAMAC", "aliases": ["cladribina", "cladribine", "mavenclad"]},
    {"n": 20, "nombre": "Daratumumab", "programa": "DAMAC", "aliases": ["daratumumab", "darzalex"]},
    {"n": 21, "nombre": "Dasatinib", "programa": "DAMAC", "aliases": ["dasatinib", "sprycel"]},
    {"n": 22, "nombre": "Deferasirox", "programa": "DAMAC", "aliases": ["deferasirox", "exjade", "jadenu"]},
    {"n": 23, "nombre": "Dornasa alfa", "programa": "DAMAC", "aliases": ["dornasa", "dornase", "pulmozyme"]},
    {"n": 24, "nombre": "Eltrombopag", "programa": "DAMAC", "aliases": ["eltrombopag", "revolade", "promacta"]},
    {"n": 25, "nombre": "Emicizumab", "programa": "DAMAC", "aliases": ["emicizumab", "hemlibra"]},
    {"n": 26, "nombre": "Enzalutamida", "programa": "DAMAC", "aliases": ["enzalutamida", "enzalutamide", "xtandi"]},
    {"n": 27, "nombre": "Etanercept", "programa": "DAMAC-FOMAC", "aliases": ["etanercept", "enbrel", "brenzys", "erelzi"]},
    {"n": 28, "nombre": "Everolimus", "programa": "DAMAC", "aliases": ["everolimus", "afinitor", "certican"]},
    {"n": 29, "nombre": "Factor de coagulación VIII", "programa": "DAMAC", "aliases": ["factor viii", "factor 8", "octocog", "moroctocog", "antihemophilic", "advate", "xyntha"]},
    {"n": 30, "nombre": "Factor de crecimiento epidérmico humano recombinante", "programa": "DAMAC", "aliases": ["factor de crecimiento epidermico", "epidermal growth factor", "heberprot", "rh-egf", "rhegf"]},
    {"n": 31, "nombre": "Factor IX", "programa": "DAMAC", "aliases": ["factor ix", "factor 9", "nonacog", "benefix", "alprolix"]},
    {"n": 32, "nombre": "Filgrastim", "programa": "DAMAC", "aliases": ["filgrastim", "neupogen", "filatil"]},
    {"n": 33, "nombre": "Fingolimod", "programa": "DAMAC", "aliases": ["fingolimod", "gilenya"]},
    {"n": 34, "nombre": "Fulvestrant", "programa": "DAMAC", "aliases": ["fulvestrant", "faslodex"]},
    {"n": 35, "nombre": "Galsulfasa", "programa": "DAMAC", "aliases": ["galsulfasa", "galsulfase", "naglazyme"]},
    {"n": 36, "nombre": "Golimumab", "programa": "DAMAC-FOMAC", "aliases": ["golimumab", "simponi"]},
    {"n": 37, "nombre": "Guselkumab", "programa": "DAMAC", "aliases": ["guselkumab", "tremfya"]},
    {"n": 38, "nombre": "Ibrutinib", "programa": "DAMAC", "aliases": ["ibrutinib", "imbruvica"]},
    {"n": 39, "nombre": "Imatinib", "programa": "DAMAC", "aliases": ["imatinib", "gleevec", "glivec"]},
    {"n": 40, "nombre": "Imiglucerasa", "programa": "DAMAC", "aliases": ["imiglucerasa", "imiglucerase", "cerezyme"]},
    {"n": 41, "nombre": "Infliximab", "programa": "DAMAC-FOMAC", "aliases": ["infliximab", "remicade", "remsima", "inflectra"]},
    {"n": 42, "nombre": "Inmunoglobulina humana", "programa": "DAMAC", "aliases": ["inmunoglobulina", "immunoglobulin", "imunoglobulina", "ivig", "gamunex", "privigen", "flebogamma"]},
    {"n": 43, "nombre": "Interferón beta 1A", "programa": "DAMAC", "aliases": ["interferon beta-1a", "interferon beta 1a", "interferon beta 1-a", "interferona beta 1a", "avonex", "rebif", "plegridy"]},
    {"n": 44, "nombre": "Interferón beta 1B", "programa": "DAMAC", "aliases": ["interferon beta-1b", "interferon beta 1b", "interferona beta 1b", "betaseron", "betaferon", "extavia"]},
    {"n": 45, "nombre": "Lapatinib ditosilato", "programa": "DAMAC", "aliases": ["lapatinib", "tykerb", "tyverb"]},
    {"n": 46, "nombre": "Lenalidomida", "programa": "DAMAC", "aliases": ["lenalidomida", "lenalidomide", "revlimid"]},
    {"n": 47, "nombre": "Letrozol", "programa": "DAMAC", "aliases": ["letrozol", "letrozole", "femara"]},
    {"n": 48, "nombre": "Micofenolato mofetilo", "programa": "DAMAC", "aliases": ["micofenolato mofetilo", "mycophenolate mofetil", "cellcept"]},
    {"n": 49, "nombre": "Micofenolato sódico", "programa": "DAMAC", "aliases": ["micofenolato sodico", "mycophenolate sodium", "myfortic"]},
    {"n": 50, "nombre": "Nilotinib", "programa": "DAMAC", "aliases": ["nilotinib", "tasigna"]},
    {"n": 51, "nombre": "Obinutuzumab", "programa": "DAMAC", "aliases": ["obinutuzumab", "gazyva", "gazyvaro"]},
    {"n": 52, "nombre": "Ocrelizumab", "programa": "DAMAC", "aliases": ["ocrelizumab", "ocrevus"]},
    {"n": 53, "nombre": "Octreotida", "programa": "DAMAC-FOMAC", "aliases": ["octreotida", "octreotide", "sandostatin", "sandostatina"]},
    {"n": 54, "nombre": "Olaparib", "programa": "DAMAC", "aliases": ["olaparib", "lynparza"]},
    {"n": 55, "nombre": "Omalizumab", "programa": "DAMAC", "aliases": ["omalizumab", "xolair"]},
    {"n": 56, "nombre": "Osimertinib mesilato", "programa": "DAMAC", "aliases": ["osimertinib", "tagrisso"]},
    {"n": 57, "nombre": "Palbociclib", "programa": "DAMAC-FOMAC", "aliases": ["palbociclib", "palbociclibe", "ibrance"]},
    {"n": 58, "nombre": "Palmitato de paliperidona", "programa": "DAMAC", "aliases": ["paliperidona", "paliperidone", "invega", "xeplion", "trinza"]},
    {"n": 59, "nombre": "Pembrolizumab", "programa": "DAMAC-FOMAC", "aliases": ["pembrolizumab", "pembrolizumabe", "keytruda"]},
    {"n": 60, "nombre": "Pertuzumab", "programa": "DAMAC", "aliases": ["pertuzumab", "perjeta"]},
    {"n": 61, "nombre": "Pertuzumab/Trastuzumab", "programa": "DAMAC", "aliases": ["pertuzumab y trastuzumab", "pertuzumab/trastuzumab", "phesgo"]},
    {"n": 62, "nombre": "Pirfenidona", "programa": "DAMAC", "aliases": ["pirfenidona", "pirfenidone", "esbriet"]},
    {"n": 63, "nombre": "Regorafenib", "programa": "DAMAC", "aliases": ["regorafenib", "stivarga"]},
    {"n": 64, "nombre": "Remdesivir", "programa": "DAMAC", "aliases": ["remdesivir", "veklury"]},
    {"n": 65, "nombre": "Ribociclib", "programa": "DAMAC-FOMAC", "aliases": ["ribociclib", "kisqali"]},
    {"n": 66, "nombre": "Riluzol", "programa": "DAMAC", "aliases": ["riluzol", "riluzole", "rilutek"]},
    {"n": 67, "nombre": "Riociguat", "programa": "DAMAC", "aliases": ["riociguat", "adempas"]},
    {"n": 68, "nombre": "Rituximab", "programa": "DAMAC", "aliases": ["rituximab", "mabthera", "rituxan"]},
    {"n": 69, "nombre": "Secukinumab", "programa": "DAMAC", "aliases": ["secukinumab", "cosentyx"]},
    {"n": 70, "nombre": "Sirolimus", "programa": "DAMAC", "aliases": ["sirolimus", "rapamune"]},
    {"n": 71, "nombre": "Sofosbuvir/Velpatasvir", "programa": "DAMAC", "aliases": ["sofosbuvir", "velpatasvir", "epclusa"]},
    {"n": 72, "nombre": "Somatropina", "programa": "DAMAC", "aliases": ["somatropina", "somatropin", "genotropin", "norditropin", "saizen", "humatrope"]},
    {"n": 73, "nombre": "Sorafenib tosilato", "programa": "DAMAC", "aliases": ["sorafenib", "nexavar"]},
    {"n": 74, "nombre": "Sunitinib", "programa": "DAMAC", "aliases": ["sunitinib", "sutent"]},
    {"n": 75, "nombre": "Tacrolimus", "programa": "DAMAC", "aliases": ["tacrolimus", "prograf", "advagraf"]},
    {"n": 76, "nombre": "Teriflunomida", "programa": "DAMAC", "aliases": ["teriflunomida", "teriflunomide", "aubagio"]},
    {"n": 77, "nombre": "Teriparatida", "programa": "DAMAC", "aliases": ["teriparatida", "teriparatide", "forteo"]},
    {"n": 78, "nombre": "Timoglobulina de conejo (antitimocitos humana)", "programa": "DAMAC", "aliases": ["timoglobulina", "thymoglobulin", "antitimocito", "antithymocyte", "atg"]},
    {"n": 79, "nombre": "Tocilizumab", "programa": "DAMAC-FOMAC", "aliases": ["tocilizumab", "actemra", "roactemra"]},
    {"n": 80, "nombre": "Tofacitinib", "programa": "DAMAC", "aliases": ["tofacitinib", "xeljanz"]},
    {"n": 81, "nombre": "Trastuzumab", "programa": "DAMAC", "aliases": ["trastuzumab", "herceptin"]},
    {"n": 82, "nombre": "Ustekinumab", "programa": "DAMAC-FOMAC", "aliases": ["ustekinumab", "stelara"]},
    {"n": 83, "nombre": "Valganciclovir", "programa": "DAMAC", "aliases": ["valganciclovir", "valcyte"]},
    {"n": 84, "nombre": "Blinatumomab", "programa": "FOMAC", "aliases": ["blinatumomab", "blincyto"]},
    {"n": 85, "nombre": "PEG-ASP (pegilada)", "programa": "FOMAC", "aliases": ["pegaspargasa", "pegaspargase", "peg-asp", "oncaspar", "asparaginasa pegilada"]},
    {"n": 86, "nombre": "Risdiplam", "programa": "FOMAC", "aliases": ["risdiplam", "evrysdi"]},
    {"n": 87, "nombre": "Pegfilgrastim", "programa": "FOMAC*", "aliases": ["pegfilgrastim", "pegfilgastrim", "neulasta", "neulastim", "ristempa", "ziextenzo", "fulphila"]},
    {"n": 88, "nombre": "Palonosetrón", "programa": "FOMAC*", "aliases": ["palonosetron", "palonosetrona", "aloxi", "onicit"]},
]


from marcas import aliases_de_marcas  # noqa: E402


def _mezclar_marcas() -> None:
    for med in MEDICAMENTOS:
        vistos = {str(a).strip().lower() for a in med["aliases"]}
        for alias in aliases_de_marcas(int(med["n"])):
            if alias not in vistos:
                med["aliases"].append(alias)
                vistos.add(alias)


_mezclar_marcas()


def prioridad(programa: str) -> int:
    p = programa.upper()
    if p == "FOMAC":
        return 0
    if p == "FOMAC*":
        return 1
    if "FOMAC" in p:
        return 2
    return 3
