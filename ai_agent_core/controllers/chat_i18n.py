"""Odoo translation markers for the standalone chat page; UI text only."""
import json
import re
from babel.messages.jslexer import tokenize, unquote_string
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)

CHAT_LABELS = {
    'Start a conversation': _lt('Start a conversation'),
    'Search conversations...': _lt('Search conversations...'),
    'Enter to send': _lt('Enter to send'),
    'Ask a question to start chatting with your assistant.': _lt('Ask a question to start chatting with your assistant.'),
    'AI Chat': _lt('AI Chat'),
    'Allmän assistent': _lt('Allmän assistent'),
    'General Assistant': _lt('General Assistant'),
    '(inga argument)': _lt('(inga argument)'),
    '(inget svar)': _lt('(inget svar)'),
    '+ Ny tråd': _lt('+ Ny tråd'),
    '. Agenten svarar baserat på sin konfiguration och dina instruktioner.': _lt('. Agenten svarar baserat på sin konfiguration och dina instruktioner.'),
    'Agenten behöver input': _lt('Agenten behöver input'),
    'Aktivera push-notiser': _lt('Aktivera push-notiser'),
    'Analysera vår nuvarande marknadsposition': _lt('Analysera vår nuvarande marknadsposition'),
    'Anslutningen till AI-servern bröts — försök igen.': _lt('Anslutningen till AI-servern bröts — försök igen.'),
    'Avbryt': _lt('Avbryt'),
    'Bearbetar…': _lt('Bearbetar…'),
    'Berätta om dina funktioner': _lt('Berätta om dina funktioner'),
    'Bra svar': _lt('Bra svar'),
    'Chattar med': _lt('Chattar med'),
    'Code Assistant': _lt('Code Assistant'),
    'Denna tråd har inga meddelanden än.': _lt('Denna tråd har inga meddelanden än.'),
    'Ditt svar...': _lt('Ditt svar...'),
    'Dåligt svar': _lt('Dåligt svar'),
    'Fel: ': _lt('Fel: '),
    'Fäst tråd': _lt('Fäst tråd'),
    'Förhandsvisning': _lt('Förhandsvisning'),
    'Förklara hur denna SQL-fråga fungerar': _lt('Förklara hur denna SQL-fråga fungerar'),
    'Förklara periodiseringsfond för aktiebolag': _lt('Förklara periodiseringsfond för aktiebolag'),
    'Godkänn verktyg: ': _lt('Godkänn verktyg: '),
    'Hitta och fixa buggar i min kod': _lt('Hitta och fixa buggar i min kod'),
    'Hur bokför jag en leverantörsfaktura med moms?': _lt('Hur bokför jag en leverantörsfaktura med moms?'),
    'Hur kommer jag igång?': _lt('Hur kommer jag igång?'),
    'Identifiera våra tre största tillväxtmöjligheter': _lt('Identifiera våra tre största tillväxtmöjligheter'),
    'Inga skills bundna till denna agent. Lägg till skills via agent-inställningarna.': _lt('Inga skills bundna till denna agent. Lägg till skills via agent-inställningarna.'),
    'Inga skills matchar "': _lt('Inga skills matchar "'),
    'Ingen VAPID-nyckel på servern': _lt('Ingen VAPID-nyckel på servern'),
    'Kopiera': _lt('Kopiera'),
    'Kostnad: $': _lt('Kostnad: $'),
    'Kunde inte skapa tråden': _lt('Kunde inte skapa tråden'),
    'Kunde inte skapa tråden: ': _lt('Kunde inte skapa tråden: '),
    'Kör…': _lt('Kör…'),
    'Klar': _lt('Klar'),
    'Ladda upp bild': _lt('Ladda upp bild'),
    'Ladda upp dokument': _lt('Ladda upp dokument'),
    'Ladda ner ': _lt('Ladda ner '),
    'Laddar skills...': _lt('Laddar skills...'),
    'Meny': _lt('Meny'),
    'Namn': _lt('Namn'),
    'Notiser blockerade i webbläsaren': _lt('Notiser blockerade i webbläsaren'),
    'Okant svar': _lt('Okant svar'),
    'Okant': _lt('Okant'),
    'Pågår: ~': _lt('Pågår: ~'),
    'Redigera tråd': _lt('Redigera tråd'),
    'Remove failed': _lt('Remove failed'),
    'Skapa en resultaträkning för senaste kvartalet': _lt('Skapa en resultaträkning för senaste kvartalet'),
    'Skapa ett strategiskt initiativ för nästa kvartal': _lt('Skapa ett strategiskt initiativ för nästa kvartal'),
    'Skicka': _lt('Skicka'),
    'Skriv en Python-funktion för att parsa CSV': _lt('Skriv en Python-funktion för att parsa CSV'),
    'Skriv ett meddelande...': _lt('Skriv ett meddelande...'),
    'Spara': _lt('Spara'),
    'Strategy Composer': _lt('Strategy Composer'),
    'Ställ en fråga eller välj en agent i sidopanelen för att komma igång.': _lt('Ställ en fråga eller välj en agent i sidopanelen för att komma igång.'),
    'Ställ en fråga för att starta en konversation med ': _lt('Ställ en fråga för att starta en konversation med '),
    'Stäng': _lt('Stäng'),
    'Svara': _lt('Svara'),
    'Swedish Accounting': _lt('Swedish Accounting'),
    'Ta bort fästning': _lt('Ta bort fästning'),
    'Tillbaka till backend': _lt('Tillbaka till backend'),
    'Tråd': _lt('Tråd'),
    'Trådnamn...': _lt('Trådnamn...'),
    'Vad kan du hjälpa mig med?': _lt('Vad kan du hjälpa mig med?'),
    'Välj en agent först — klicka på en agent i sidopanelen': _lt('Välj en agent först — klicka på en agent i sidopanelen'),
    'Välj en quest först!': _lt('Välj en quest först!'),
    'Växla tema': _lt('Växla tema'),
    'förbrukning ej rapporterad': _lt('förbrukning ej rapporterad'),
    'verktygsanrop': _lt('verktygsanrop'),
    '⏳ Aktiverar…': _lt('⏳ Aktiverar…'),
    '✓ Notiser aktiverade': _lt('✓ Notiser aktiverade'),
    '❌ Avbrutet av användaren': _lt('❌ Avbrutet av användaren'),
    '❌ Nätverksfel': _lt('❌ Nätverksfel'),
    'Nätverksfel': _lt('Nätverksfel'),
    '📄 Dokument': _lt('📄 Dokument'),
    '📌 Fästa trådar': _lt('📌 Fästa trådar'),
    '📎 Laddar upp ': _lt('📎 Laddar upp '),
    '🔍 Debug': _lt('🔍 Debug'),
    '🔍 Sök trådar...': _lt('🔍 Sök trådar...'),
    '🔔 Aktivera notiser': _lt('🔔 Aktivera notiser'),
    '🔔 Försök igen': _lt('🔔 Försök igen'),
    '🔔 Notiser aktiva (registrera om)': _lt('🔔 Notiser aktiva (registrera om)'),
    '🔗 källor': _lt('🔗 källor'),
    '🧠 Resonemang': _lt('🧠 Resonemang'),
    ' tokens': _lt(' tokens'),
    ' d sen': _lt(' d sen'),
    ' h sen': _lt(' h sen'),
    ' min sen': _lt(' min sen'),
}

def _localize_script(script, translate):
    """Only translate string literals; leave JavaScript tokens and prompts intact."""
    fragments = []
    position = 0
    for token in tokenize(script):
        start = script.find(token.value, position)
        if start < 0:
            return script
        fragments.append(script[position:start])
        value = token.value
        if token.type == "string":
            text = unquote_string(value)
            translated = translate(text)
            if translated != text:
                value = json.dumps(translated, ensure_ascii=False).replace("</", "<\\/")
        fragments.append(value)
        position = start + len(token.value)
    fragments.append(script[position:])
    return "".join(fragments)


def localize_chat_template(template, env):
    """Use the Odoo catalog for chat display text; never translate code or CSS."""
    translations = {source: str(env._(label)) for source, label in CHAT_LABELS.items()}
    pattern = re.compile("|".join(re.escape(source) for source in sorted(translations, key=len, reverse=True)))
    def translate(text):
        return pattern.sub(lambda match: translations[match.group(0)], text)
    sections = re.split(r"(<(?:script|style)\b[^>]*>.*?</(?:script|style)>)", template, flags=re.S | re.I)
    for index, section in enumerate(sections):
        if section.lower().startswith("<script"):
            opening, body = section.split(">", 1)
            script, closing = body.rsplit("</", 1)
            sections[index] = opening + ">" + _localize_script(script, translate) + "</" + closing
        elif not section.lower().startswith("<style"):
            sections[index] = translate(section)
    template = "".join(sections)
    return template.replace('<html lang="sv"', '<html lang="%s"' % env.lang.replace("_", "-"))
