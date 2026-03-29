"""
Mock data for SBITIS platform tests.

Realistic fixtures that mirror what Fireflies, GHL, Meta Ads, and Google Sheets
actually return so we can test the full pipeline without any network calls.
"""

from datetime import datetime, timedelta

# ── Fireflies GraphQL responses ───────────────────────────────────────────────

MOCK_FIREFLIES_STRATEGY_CALL = {
    "id": "test-strategy-001",
    "title": "Strategy Call - Youssef Benali",
    "date": (datetime.utcnow() - timedelta(hours=5)).isoformat() + "Z",
    "duration": 2700,
    "meeting_attendees": [
        {"displayName": "Hamza SBITI"},
        {"displayName": "Youssef Benali"},
    ],
    # Sentences at top level — how Fireflies GraphQL actually returns data
    "sentences": [
            {"text": "Hamza: Bonjour Youssef, merci d'être là. Comment ça va?", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: Ça va bien, merci. J'ai regardé votre contenu sur Instagram.", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: Super. Parle-moi de ton business, qu'est-ce que tu fais exactement?", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: On vend des produits d'artisanat marocain, on a une boutique à Casablanca et on essaie de vendre en ligne aussi.", "speaker_name": "Youssef Benali"},
            {"text": "Youssef: Le problème c'est qu'on fait de la pub Facebook mais ça marche pas bien. On dépense 5000 dirhams par mois et on a presque rien.", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: D'accord, et tu gères ça toi-même ou t'as quelqu'un?", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: Moi-même mais je comprends rien au ciblage et tout ça.", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: Ok, laisse-moi t'expliquer ce qu'on fait chez SBITIS. On prend en charge toute ta publicité, de A à Z. Tu touches plus à rien.", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: Ça coûte combien?", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: Notre offre DFY c'est 3500 dirhams par mois, tout inclus.", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: C'est cher quand même. J'suis pas sûr que ça vaut le coup pour nous.", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: Youssef, tu dépenses déjà 5000 MAD et tu as zéro résultat. Avec nous, tu paies 3500 et on optimise ton budget pub en plus.", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: Ah ouais, vu comme ça... Mais j'ai besoin d'en parler avec mon associé.", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: Je comprends. Tu peux lui en parler quand?", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: Cette semaine normalement. Je vous rappelle jeudi.", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: Parfait. Je vais t'envoyer notre contrat sur WhatsApp pour que tu puisses le montrer à ton associé.", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: D'accord, je vais l'appeler ce soir pour lui en parler.", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: Parfait. Est-ce que tu peux me dire, c'est quoi la principale raison pour laquelle tu n'as pas encore délégué ta pub?", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: Honnêtement, j'avais peur de pas avoir de résultats et de perdre mon argent.", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: C'est une peur légitime. C'est pour ça qu'on commence avec un contrat d'essai de 30 jours.", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: 30 jours c'est court pour voir des résultats non?", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: On va optimiser dès la première semaine. Nos clients voient généralement les premières leads dans les 72 heures.", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: Vraiment? Parce que j'avais une agence avant et ils ont mis 2 mois pour rien.", "speaker_name": "Youssef Benali"},
            {"text": "Hamza: Exactement le problème qu'on résout. Nos process sont différents, on t'expliquera tout lors du onboarding.", "speaker_name": "Hamza SBITI"},
            {"text": "Youssef: OK je vais vraiment en parler à mon associé. Je pense qu'on peut aller de l'avant.", "speaker_name": "Youssef Benali"},
    ],
    "summary": {
        "gist": "Strategy call with Youssef Benali about DFY digital marketing for his Moroccan artisan e-commerce business.",
        "overview": "Youssef runs an artisan products shop in Casablanca with online presence. Spending 5000 MAD/month on Facebook ads with poor results. Interested in DFY offer at 3500 MAD/month but needs to consult with business partner before deciding.",
        "action_items": ["Send contract on WhatsApp", "Follow up Thursday"],
        "keywords": ["DFY", "Facebook ads", "artisanat", "3500 MAD", "associé"],
    },
}

MOCK_FIREFLIES_TRAINING_CALL = {
    "id": "test-training-001",
    "title": "Sales Training Session - Weekly Review",
    "date": (datetime.utcnow() - timedelta(hours=8)).isoformat() + "Z",
    "duration": 3600,
    "meeting_attendees": [
        {"displayName": "Hamza SBITI"},
        {"displayName": "Zineb Lahbabi"},
        {"displayName": "Chakir"},
    ],
    "sentences": [
        {"text": "Hamza: Bon, on va revoir les appels de cette semaine. Zineb, commence.", "speaker_name": "Hamza SBITI"},
        {"text": "Zineb: J'ai eu 4 calls. 1 WON, 2 LOST, 1 PENDING.", "speaker_name": "Zineb Lahbabi"},
        {"text": "Hamza: Le WON, comment tu l'as closé?", "speaker_name": "Hamza SBITI"},
        {"text": "Zineb: J'ai utilisé la technique du budget actuel. Il dépensait déjà 8000 MAD sur de la pub qui marchait pas.", "speaker_name": "Zineb Lahbabi"},
        {"text": "Hamza: Parfait. Les LOST, pourquoi?", "speaker_name": "Hamza SBITI"},
        {"text": "Zineb: Premier LOST, il voulait faire lui-même. Deuxième LOST, objectif trop petit.", "speaker_name": "Zineb Lahbabi"},
        {"text": "Hamza: Le 'je veux faire moi-même', t'as utilisé quoi comme réponse?", "speaker_name": "Hamza SBITI"},
        {"text": "Zineb: J'ai dit que notre expertise va plus vite mais il était pas convaincu.", "speaker_name": "Zineb Lahbabi"},
        {"text": "Hamza: La prochaine fois, demande-lui combien d'heures il passe sur la pub par semaine. Puis calcule ce que ça lui coûte en temps.", "speaker_name": "Hamza SBITI"},
        {"text": "Chakir: Moi j'ai eu 3 calls. 0 WON. Les gens disent tous que c'est trop cher.", "speaker_name": "Chakir"},
        {"text": "Hamza: Chakir, le prix c'est jamais le vrai problème. C'est que tu as pas bien établi la valeur avant de donner le prix.", "speaker_name": "Hamza SBITI"},
        {"text": "Chakir: Ok mais comment j'établis la valeur quand ils demandent le prix dès le début?", "speaker_name": "Chakir"},
        {"text": "Hamza: Tu dis 'on va y venir, mais d'abord dis-moi combien tu dépenses en pub en ce moment et quels résultats tu as.' Ça recadre tout.", "speaker_name": "Hamza SBITI"},
        {"text": "Zineb: C'est ce que j'ai fait sur mon WON de cette semaine exactement.", "speaker_name": "Zineb Lahbabi"},
        {"text": "Hamza: Exactement. On parle du ROI avant le prix. Chakir, rejoue le call de jeudi avec moi.", "speaker_name": "Hamza SBITI"},
        {"text": "Chakir: D'accord. Bonjour, je vous appelle de la part de SBITIS...", "speaker_name": "Chakir"},
        {"text": "Hamza: Stop. Tu commences par le script de qualification, pas la présentation. Recommence.", "speaker_name": "Hamza SBITI"},
        {"text": "Chakir: Ok. Bonjour, j'espère que vous allez bien. Vous gérez votre pub Facebook vous-même?", "speaker_name": "Chakir"},
        {"text": "Hamza: Beaucoup mieux. Continue.", "speaker_name": "Hamza SBITI"},
        {"text": "Zineb: Je pense que Chakir a aussi un problème avec le silence après avoir donné le prix.", "speaker_name": "Zineb Lahbabi"},
        {"text": "Hamza: Très bonne observation. Chakir, après avoir dit le prix, tu te tais. Tu attends. C'est le prospect qui parle en premier.", "speaker_name": "Hamza SBITI"},
        {"text": "Chakir: C'est difficile, j'ai toujours envie de remplir le silence.", "speaker_name": "Chakir"},
        {"text": "Hamza: C'est normal. Mais celui qui parle après le prix en premier, c'est lui qui perd. Entraîne-toi à tenir 15 secondes de silence.", "speaker_name": "Hamza SBITI"},
    ],
    "summary": {
        "gist": "Weekly sales training session reviewing call performance for Zineb and Chakir.",
        "overview": "Zineb closed 1, lost 2. Chakir closed 0. Main issues: Chakir presenting price before establishing value, Zineb needs stronger 'DIY objection' reframe.",
        "action_items": ["Chakir to practice value-first framework", "Zineb to use time-cost calculation for DIY objection"],
        "keywords": ["training", "objection handling", "closing", "value", "prix"],
    },
}

MOCK_FIREFLIES_APPOINTMENT = {
    "id": "test-appt-001",
    "title": "Confirmation appel Rachid",
    "date": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z",
    "duration": 180,
    "meeting_attendees": [
        {"displayName": "Zineb Lahbabi"},
        {"displayName": "Rachid"},
    ],
    "sentences": [
        {"text": "Zineb: Bonjour Rachid, c'est Zineb de SBITIS. Je vous appelle pour confirmer votre appel de demain à 15h.", "speaker_name": "Zineb Lahbabi"},
        {"text": "Rachid: Oui, c'est bon pour moi.", "speaker_name": "Rachid"},
        {"text": "Zineb: Parfait, à demain.", "speaker_name": "Zineb Lahbabi"},
    ],
    "summary": {
        "gist": "Short appointment confirmation call.",
        "overview": "Zineb confirms appointment with Rachid for tomorrow at 3pm.",
        "action_items": [],
        "keywords": ["confirmation", "rendez-vous"],
    },
}

# Raw Fireflies GraphQL transcript list response
MOCK_FIREFLIES_API_RESPONSE = {
    "data": {
        "transcripts": [
            MOCK_FIREFLIES_STRATEGY_CALL,
            MOCK_FIREFLIES_TRAINING_CALL,
            MOCK_FIREFLIES_APPOINTMENT,
        ]
    }
}

# ── Meta Ads API response ─────────────────────────────────────────────────────

MOCK_META_CAMPAIGN_INSIGHTS = [
    {
        "campaign_id": "120201234567890",
        "campaign_name": "DFY - Lead Gen - Maroc - Lookalike",
        "adset_name": "DFY LAL 3% Maroc",
        "spend": "4250.00",
        "impressions": "98500",
        "clicks": "1240",
        "ctr": "1.259",
        "actions": [{"action_type": "lead", "value": "34"}],
    },
    {
        "campaign_id": "120201234567891",
        "campaign_name": "DFY - Retargeting - Visiteurs site",
        "adset_name": "DFY Retarget 30j",
        "spend": "1800.00",
        "impressions": "45000",
        "clicks": "890",
        "ctr": "1.978",
        "actions": [{"action_type": "lead", "value": "22"}],
    },
    {
        "campaign_id": "120201234567892",
        "campaign_name": "DWY - Formation - Entrepreneurs",
        "adset_name": "DWY Cold Intérêts",
        "spend": "2100.00",
        "impressions": "67000",
        "clicks": "780",
        "ctr": "1.164",
        "actions": [{"action_type": "lead", "value": "18"}],
    },
    {
        "campaign_id": "120201234567893",
        "campaign_name": "Brand Awareness - Hamza SBITI",
        "adset_name": "Brand All Morocco",
        "spend": "800.00",
        "impressions": "120000",
        "clicks": "420",
        "ctr": "0.350",
        "actions": [],
    },
]

# ── Google Sheets responses ───────────────────────────────────────────────────

MOCK_CLOSER_METRICS = [
    {
        "closer_name": "Hamza SBITI",
        "calls_taken": 8,
        "won": 4,
        "lost": 2,
        "pending": 1,
        "maybe": 1,
        "close_rate": 66.7,
        "revenue_collected": 14000.0,
    },
    {
        "closer_name": "Zineb Lahbabi",
        "calls_taken": 4,
        "won": 1,
        "lost": 2,
        "pending": 1,
        "maybe": 0,
        "close_rate": 33.3,
        "revenue_collected": 3500.0,
    },
    {
        "closer_name": "Chakir",
        "calls_taken": 6,
        "won": 0,
        "lost": 3,
        "pending": 2,
        "maybe": 1,
        "close_rate": 0.0,
        "revenue_collected": 0.0,
    },
]

MOCK_FUNNEL_METRICS = {
    "leads_generated": 74,
    "booked_meetings": 28,
    "showed_meetings": 19,
    "closed": 5,
    "show_rate": 67.9,
    "close_rate": 26.3,
    "cash_collected": 17500,
    "currency": "MAD",
}

# ── GHL pipeline response ─────────────────────────────────────────────────────

MOCK_GHL_PIPELINE = {
    "pipeline_id": "test-pipeline-001",
    "pipeline_name": "SBITIS DFY Sales Pipeline",
    "total_contacts": 47,
    "stages": {
        "New Lead": {"count": 12, "value": 0},
        "Qualified": {"count": 8, "value": 0},
        "Call Booked": {"count": 7, "value": 0},
        "Call Done": {"count": 6, "value": 0},
        "Proposal Sent": {"count": 4, "value": 14000},
        "WON": {"count": 5, "value": 17500},
        "LOST": {"count": 5, "value": 0},
    },
    "by_tag": {
        "DFY": 31,
        "DWY": 9,
        "Not Qualified": 7,
    },
    "by_closer": {
        "Hamza SBITI": {"total": 18, "won": 4},
        "Zineb Lahbabi": {"total": 12, "won": 1},
        "Chakir": {"total": 10, "won": 0},
        "Austin": {"total": 7, "won": 0},
    },
}

# ── LLM analysis response fixtures ───────────────────────────────────────────

MOCK_STRATEGY_ANALYSIS_JSON = {
    "file_id": "test-strategy-001",
    "call_date": datetime.utcnow().strftime("%Y-%m-%d"),
    "closer_name": "Hamza SBITI",
    "prospect_name": "Youssef Benali",
    "outcome": "MAYBE",
    "duration_estimate": "Medium (30-60 min)",
    "language_detected": "Mix",
    "prospect_profile": {
        "business_type": "E-commerce / Artisanat marocain",
        "current_situation": "Boutique physique à Casablanca + vente en ligne. Budget pub 5000 MAD/mois avec faibles résultats.",
        "main_pain_points": [
            "Publicité Facebook inefficace",
            "Pas de compétences en ciblage",
            "Retour sur investissement nul",
        ],
    },
    "value_offer": "DFY — gestion complète de la publicité à 3500 MAD/mois",
    "currency": "MAD",
    "ghl_tag": "DFY",
    "main_objections": [
        "C'est cher — 3500 MAD semble élevé",
        "Besoin de consulter l'associé avant de décider",
    ],
    "objection_handling": 7,
    "objection_handling_notes": "Hamza a bien utilisé le reframe du budget actuel (5000 MAD gaspillé vs 3500 MAD investi). L'objection de l'associé n'a pas été creusée — est-ce vraiment un blocker ou une excuse?",
    "positioning_gaps": [
        "N'a pas montré de résultats concrets (ROI clients DFY)",
        "Pas de proof social adapté à l'artisanat/e-commerce",
    ],
    "buying_signals": [
        "'Ah ouais, vu comme ça...' — acceptation du reframe budget",
        "A accepté de recevoir le contrat sur WhatsApp",
        "A donné une date précise de rappel (jeudi)",
    ],
    "close_attempt": "Hamza a demandé quand Youssef pouvait parler à son associé et s'est positionné pour un follow-up jeudi.",
    "close_quality": 6,
    "close_quality_notes": "Close propre mais l'objection de l'associé aurait pu être challengée davantage. Aurait pu proposer de les appeler ensemble.",
    "key_moments": [
        {
            "timestamp_approx": "Début de l'appel",
            "description": "Youssef mentionne qu'il a découvert SBITIS via Instagram — confirme que le contenu Hamza fonctionne pour attirer des leads qualifiés.",
        },
        {
            "timestamp_approx": "Milieu — objection prix",
            "description": "Hamza retourne l'objection avec le budget existant (5000 MAD gaspillé). Moment pivot de l'appel.",
        },
    ],
    "recommended_improvements": [
        "Challenger l'objection 'associé' : 'Il est disponible maintenant? On peut l'appeler ensemble?'",
        "Ajouter un case study client dans le secteur e-commerce/retail pour ce type de prospect",
        "Envoyer le contrat AVANT de raccrocher — ne pas laisser le suivi ouvert",
    ],
    "fireflies_summary": "Strategy call with Youssef Benali about DFY digital marketing for his Moroccan artisan e-commerce business.",
}
