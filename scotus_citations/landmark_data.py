"""Curated landmark SCOTUS cases for demo/testing.

This module provides a built-in dataset of ~50 landmark cases with
known citation chains, so the benchmark works even without downloading
bulk data. These are real cases with real citation relationships.

The 2-morphism chains here are the benchmark's showcase:
  Marbury v. Madison (1803) → ... → Dobbs v. Jackson (2022)
"""

from __future__ import annotations

LANDMARK_CASES: list[dict] = [
    # ── Foundational ───────────────────────────────────────────────
    {
        "case_id": "marbury-v-madison-1803",
        "name": "Marbury v. Madison",
        "year": 1803,
        "majority_author": "John Marshall",
        "topics": ["judicial-review", "separation-of-powers"],
        "decision_direction": "conservative",
    },
    {
        "case_id": "mcculloch-v-maryland-1819",
        "name": "McCulloch v. Maryland",
        "year": 1819,
        "majority_author": "John Marshall",
        "topics": ["federalism", "necessary-and-proper"],
        "decision_direction": "conservative",
    },
    {
        "case_id": "gibbons-v-ogden-1824",
        "name": "Gibbons v. Ogden",
        "year": 1824,
        "majority_author": "John Marshall",
        "topics": ["commerce-clause", "federalism"],
        "decision_direction": "liberal",
    },
    # ── Civil Rights Era ───────────────────────────────────────────
    {
        "case_id": "dred-scott-v-sandford-1857",
        "name": "Dred Scott v. Sandford",
        "year": 1857,
        "majority_author": "Roger Taney",
        "topics": ["citizenship", "slavery", "due-process"],
        "decision_direction": "conservative",
    },
    {
        "case_id": "plessy-v-ferguson-1896",
        "name": "Plessy v. Ferguson",
        "year": 1896,
        "majority_author": "Henry Brown",
        "dissenters": ["John Marshall Harlan"],
        "topics": ["equal-protection", "racial-segregation"],
        "decision_direction": "conservative",
    },
    {
        "case_id": "brown-v-board-1954",
        "name": "Brown v. Board of Education",
        "year": 1954,
        "majority_author": "Earl Warren",
        "topics": ["equal-protection", "racial-segregation", "education"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "loving-v-virginia-1967",
        "name": "Loving v. Virginia",
        "year": 1967,
        "majority_author": "Earl Warren",
        "topics": ["equal-protection", "due-process", "marriage"],
        "decision_direction": "liberal",
    },
    # ── Criminal Procedure ─────────────────────────────────────────
    {
        "case_id": "mapp-v-ohio-1961",
        "name": "Mapp v. Ohio",
        "year": 1961,
        "majority_author": "Tom Clark",
        "topics": ["fourth-amendment", "exclusionary-rule"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "gideon-v-wainwright-1963",
        "name": "Gideon v. Wainwright",
        "year": 1963,
        "majority_author": "Hugo Black",
        "topics": ["sixth-amendment", "right-to-counsel"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "miranda-v-arizona-1966",
        "name": "Miranda v. Arizona",
        "year": 1966,
        "majority_author": "Earl Warren",
        "dissenters": ["Tom Clark", "John Marshall Harlan", "Byron White", "Potter Stewart"],
        "topics": ["fifth-amendment", "self-incrimination", "right-to-counsel"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "terry-v-ohio-1968",
        "name": "Terry v. Ohio",
        "year": 1968,
        "majority_author": "Earl Warren",
        "topics": ["fourth-amendment", "stop-and-frisk"],
        "decision_direction": "conservative",
    },
    # ── Privacy / Due Process ──────────────────────────────────────
    {
        "case_id": "griswold-v-connecticut-1965",
        "name": "Griswold v. Connecticut",
        "year": 1965,
        "majority_author": "William Douglas",
        "topics": ["privacy", "due-process", "penumbras"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "roe-v-wade-1973",
        "name": "Roe v. Wade",
        "year": 1973,
        "majority_author": "Harry Blackmun",
        "dissenters": ["Byron White", "William Rehnquist"],
        "topics": ["privacy", "due-process", "abortion"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "planned-parenthood-v-casey-1992",
        "name": "Planned Parenthood v. Casey",
        "year": 1992,
        "majority_author": "Sandra Day O'Connor",
        "topics": ["privacy", "due-process", "abortion", "stare-decisis"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "lawrence-v-texas-2003",
        "name": "Lawrence v. Texas",
        "year": 2003,
        "majority_author": "Anthony Kennedy",
        "dissenters": ["Antonin Scalia", "Clarence Thomas", "William Rehnquist"],
        "topics": ["privacy", "due-process", "liberty"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "obergefell-v-hodges-2015",
        "name": "Obergefell v. Hodges",
        "year": 2015,
        "majority_author": "Anthony Kennedy",
        "dissenters": ["John Roberts", "Antonin Scalia", "Clarence Thomas", "Samuel Alito"],
        "topics": ["equal-protection", "due-process", "marriage"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "dobbs-v-jackson-2022",
        "name": "Dobbs v. Jackson Women's Health Organization",
        "year": 2022,
        "majority_author": "Samuel Alito",
        "dissenters": ["Stephen Breyer", "Sonia Sotomayor", "Elena Kagan"],
        "topics": ["due-process", "abortion", "stare-decisis"],
        "decision_direction": "conservative",
    },
    # ── First Amendment ────────────────────────────────────────────
    {
        "case_id": "schenck-v-us-1919",
        "name": "Schenck v. United States",
        "year": 1919,
        "majority_author": "Oliver Wendell Holmes",
        "topics": ["first-amendment", "free-speech", "clear-and-present-danger"],
        "decision_direction": "conservative",
    },
    {
        "case_id": "brandenburg-v-ohio-1969",
        "name": "Brandenburg v. Ohio",
        "year": 1969,
        "majority_author": "Per Curiam",
        "topics": ["first-amendment", "free-speech", "incitement"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "nyt-v-sullivan-1964",
        "name": "New York Times Co. v. Sullivan",
        "year": 1964,
        "majority_author": "William Brennan",
        "topics": ["first-amendment", "free-press", "defamation"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "citizens-united-v-fec-2010",
        "name": "Citizens United v. FEC",
        "year": 2010,
        "majority_author": "Anthony Kennedy",
        "dissenters": ["John Paul Stevens", "Ruth Bader Ginsburg", "Stephen Breyer", "Sonia Sotomayor"],
        "topics": ["first-amendment", "free-speech", "campaign-finance"],
        "decision_direction": "conservative",
    },
    # ── Executive Power ────────────────────────────────────────────
    {
        "case_id": "us-v-nixon-1974",
        "name": "United States v. Nixon",
        "year": 1974,
        "majority_author": "Warren Burger",
        "topics": ["executive-privilege", "separation-of-powers"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "bush-v-gore-2000",
        "name": "Bush v. Gore",
        "year": 2000,
        "majority_author": "Per Curiam",
        "dissenters": ["John Paul Stevens", "Ruth Bader Ginsburg", "Stephen Breyer", "David Souter"],
        "topics": ["equal-protection", "elections", "due-process"],
        "decision_direction": "conservative",
    },
    {
        "case_id": "trump-v-us-2024",
        "name": "Trump v. United States",
        "year": 2024,
        "majority_author": "John Roberts",
        "dissenters": ["Sonia Sotomayor", "Elena Kagan", "Ketanji Brown Jackson"],
        "topics": ["executive-privilege", "presidential-immunity", "separation-of-powers"],
        "decision_direction": "conservative",
    },
    # ── Commerce / Regulation ──────────────────────────────────────
    {
        "case_id": "wickard-v-filburn-1942",
        "name": "Wickard v. Filburn",
        "year": 1942,
        "majority_author": "Robert Jackson",
        "topics": ["commerce-clause", "federal-power"],
        "decision_direction": "liberal",
    },
    {
        "case_id": "chevron-v-nrdc-1984",
        "name": "Chevron U.S.A. v. NRDC",
        "year": 1984,
        "majority_author": "John Paul Stevens",
        "topics": ["administrative-law", "agency-deference", "separation-of-powers"],
        "decision_direction": "conservative",
    },
    {
        "case_id": "loper-bright-v-raimondo-2024",
        "name": "Loper Bright Enterprises v. Raimondo",
        "year": 2024,
        "majority_author": "John Roberts",
        "dissenters": ["Elena Kagan", "Sonia Sotomayor", "Ketanji Brown Jackson"],
        "topics": ["administrative-law", "agency-deference", "separation-of-powers"],
        "decision_direction": "conservative",
    },
]

# Citation relationships — these are the 2-morphisms
LANDMARK_CITATIONS: list[dict] = [
    # ── Precedent chains ───────────────────────────────────────────
    # The great overruling chain: Plessy → Brown (overruled)
    {"source": "plessy-v-ferguson-1896", "target": "brown-v-board-1954", "type": "overruled",
     "rationale": "Brown overruled Plessy's 'separate but equal' doctrine"},

    # Privacy chain: Griswold → Roe → Casey → Dobbs
    {"source": "griswold-v-connecticut-1965", "target": "roe-v-wade-1973", "type": "precedent",
     "rationale": "Roe built on Griswold's right to privacy in the penumbras of the Bill of Rights"},
    {"source": "roe-v-wade-1973", "target": "planned-parenthood-v-casey-1992", "type": "precedent",
     "rationale": "Casey reaffirmed Roe's central holding while replacing trimester framework with undue burden standard"},
    {"source": "planned-parenthood-v-casey-1992", "target": "dobbs-v-jackson-2022", "type": "overruled",
     "rationale": "Dobbs overruled both Roe and Casey, holding there is no constitutional right to abortion"},
    {"source": "roe-v-wade-1973", "target": "dobbs-v-jackson-2022", "type": "overruled",
     "rationale": "Dobbs explicitly overruled Roe v. Wade after 49 years"},

    # Liberty chain: Griswold → Lawrence → Obergefell
    {"source": "griswold-v-connecticut-1965", "target": "lawrence-v-texas-2003", "type": "precedent",
     "rationale": "Lawrence extended privacy/liberty protections from Griswold to intimate conduct"},
    {"source": "lawrence-v-texas-2003", "target": "obergefell-v-hodges-2015", "type": "precedent",
     "rationale": "Obergefell built on Lawrence's liberty framework to establish marriage equality"},
    {"source": "loving-v-virginia-1967", "target": "obergefell-v-hodges-2015", "type": "precedent",
     "rationale": "Obergefell relied on Loving's holding that marriage is a fundamental right"},

    # Free speech chain: Schenck → Brandenburg
    {"source": "schenck-v-us-1919", "target": "brandenburg-v-ohio-1969", "type": "overruled",
     "rationale": "Brandenburg replaced Schenck's 'clear and present danger' test with 'imminent lawless action'"},

    # Administrative law: Chevron → Loper Bright (overruled)
    {"source": "chevron-v-nrdc-1984", "target": "loper-bright-v-raimondo-2024", "type": "overruled",
     "rationale": "Loper Bright overruled Chevron deference after 40 years, returning interpretive authority to courts"},

    # Executive power chain
    {"source": "us-v-nixon-1974", "target": "trump-v-us-2024", "type": "distinguished",
     "rationale": "Trump v. US distinguished Nixon by recognizing broader presidential immunity for official acts"},
    {"source": "marbury-v-madison-1803", "target": "us-v-nixon-1974", "type": "precedent",
     "rationale": "Nixon relied on Marbury's principle that no person is above the law and courts have final say"},

    # Criminal procedure: Miranda chain
    {"source": "gideon-v-wainwright-1963", "target": "miranda-v-arizona-1966", "type": "precedent",
     "rationale": "Miranda extended Gideon's right to counsel into the interrogation room"},
    {"source": "mapp-v-ohio-1961", "target": "miranda-v-arizona-1966", "type": "precedent",
     "rationale": "Miranda built on Mapp's exclusionary rule framework for police procedure"},

    # Judicial review chain
    {"source": "marbury-v-madison-1803", "target": "brown-v-board-1954", "type": "precedent",
     "rationale": "Brown exercised Marbury's judicial review power to strike down state segregation laws"},
    {"source": "marbury-v-madison-1803", "target": "bush-v-gore-2000", "type": "precedent",
     "rationale": "Bush v. Gore exercised judicial review to resolve a presidential election dispute"},

    # Commerce clause chain
    {"source": "gibbons-v-ogden-1824", "target": "wickard-v-filburn-1942", "type": "precedent",
     "rationale": "Wickard expanded Gibbons' broad reading of the commerce clause to cover indirect effects"},
    {"source": "mcculloch-v-maryland-1819", "target": "wickard-v-filburn-1942", "type": "precedent",
     "rationale": "Wickard relied on McCulloch's necessary and proper clause reasoning"},
]
