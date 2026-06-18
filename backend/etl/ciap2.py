"""
ETL CIAP-2 — Classificação Internacional de Atenção Primária, 2ª Edição

Fonte oficial: WONCA / SBMFC / e-SUS PEC (Ministério da Saúde)
PDF oficial:   https://sbmfc.org.br/wp-content/uploads/2023/08/CIAP-2.pdf
Página SBMFC:  https://sbmfc.org.br/ciap/

Os códigos seguem o padrão ICPC-2 internacional.
CodeSystem FHIR: http://hl7.org/fhir/sid/icpc-2

Dataset curado com ~600 códigos cobrindo todos os 17 capítulos,
usado no e-SUS PEC e compatível com a tabela de conversão CIAP-2 × CID-10.
"""
import json
import logging
from typing import Optional

from etl.base import BaseETL

logger = logging.getLogger(__name__)

_CAPITULOS = {
    "A": "Geral e Não Especificado",
    "B": "Sangue, Órgãos Hematopoiéticos e Linfáticos",
    "D": "Aparelho Digestivo",
    "F": "Olho",
    "H": "Ouvido",
    "K": "Aparelho Circulatório",
    "L": "Aparelho Locomotor",
    "N": "Sistema Neurológico",
    "P": "Psicológico",
    "R": "Aparelho Respiratório",
    "S": "Pele",
    "T": "Endócrino, Metabólico e Nutricional",
    "U": "Aparelho Urinário",
    "W": "Gravidez, Parto e Planejamento Familiar",
    "X": "Aparelho Genital Feminino",
    "Y": "Aparelho Genital Masculino",
    "Z": "Problemas Sociais",
}

def _comp(num: int) -> str:
    if num <= 29: return "Sintomas e queixas"
    if num <= 49: return "Procedimentos e exames"
    if num <= 59: return "Controle administrativo"
    if num <= 69: return "Encaminhamentos"
    return "Diagnósticos e doenças"

_CIAP2_CODES: list[tuple[str, str]] = [
    # ── A: Geral e Não Especificado
    ("A01","Dor generalizada/múltipla"),("A02","Calafrio"),("A03","Febre"),
    ("A04","Fraqueza/cansaço geral"),("A05","Sentir-se doente/mal"),
    ("A06","Desmaio/síncope"),("A07","Coma"),("A08","Sudorese/transpiração"),
    ("A09","Hemorragia não especificada"),("A10","Sangramento após procedimento"),
    ("A11","Dor torácica não especificada"),("A13","Preocupação com doença NE"),
    ("A16","Irritabilidade"),("A18","Preocupação com aparência física"),
    ("A21","Fatores de risco não especificados"),("A23","Sinais vitais NE"),
    ("A25","Medo de morte"),("A26","Medo de câncer NE"),
    ("A27","Medo de outras doenças"),("A28","Limitação funcional/incapacidade"),
    ("A29","Outros sintomas gerais"),("A44","Exame/rastreio preventivo"),
    ("A50","Medicina preventiva geral"),("A51","Prescrição/pedido de medicação"),
    ("A57","Certificado médico/declaração"),("A60","Encaminhamento a especialista"),
    ("A70","Tuberculose"),("A71","Sarampo"),("A72","Varicela/catapora"),
    ("A73","Malária"),("A74","Rubéola"),("A75","Mononucleose infecciosa"),
    ("A76","Exantema viral NE"),("A77","Doença viral NE"),
    ("A78","Doença infecciosa NE"),("A79","Neoplasia maligna NE"),
    ("A80","Traumatismo NE"),("A84","Intoxicação por substância"),
    ("A85","Efeito adverso de medicamento"),("A86","Efeito de corpo estranho"),
    ("A92","Alergia/reação alérgica NE"),("A96","Morte"),("A97","Sem doença"),
    ("A98","Problema de saúde preventivo"),("A99","Outra doença geral NE"),
    # ── B: Sangue
    ("B02","Linfadenopatia/gânglios aumentados"),("B75","Anemia por deficiência de ferro"),
    ("B76","Anemia por deficiência de vitamina B12"),("B77","Anemia por deficiência de folato"),
    ("B78","Anemia hereditária"),("B80","Anemia aplástica"),("B81","Outra anemia NE"),
    ("B82","Púrpura/distúrbio da coagulação"),("B87","Esplenomegalia"),
    ("B99","Outra doença de sangue/linfa"),
    # ── D: Digestivo
    ("D01","Dor abdominal/câimbras generalizadas"),("D02","Dor epigástrica"),
    ("D03","Azia/pirose"),("D06","Náusea"),("D07","Vômito"),
    ("D08","Flatulência/eructação"),("D09","Icterícia"),("D11","Diarreia"),
    ("D12","Constipação intestinal"),("D14","Melena/sangramento retal"),
    ("D15","Sangramento anal/retal"),("D16","Incontinência fecal"),
    ("D25","Medo de câncer digestivo"),("D29","Outros sintomas digestivos"),
    ("D70","Candidíase gastrointestinal"),("D72","Hepatite viral"),
    ("D73","Gastroenterite presumivelmente infecciosa"),
    ("D74","Neoplasia maligna do estômago"),("D75","Neoplasia maligna do cólon/reto"),
    ("D76","Neoplasia maligna do pâncreas"),("D77","Neoplasia maligna do fígado"),
    ("D81","Hérnia inguinal"),("D82","Hérnia do hiato"),
    ("D84","Doença de má absorção/intolerância"),("D85","Doença de Crohn"),
    ("D86","Retocolite ulcerativa"),("D87","Síndrome do intestino irritável"),
    ("D88","Apendicite"),("D94","Doença biliar"),("D95","Colecistite/cálculo biliar"),
    ("D96","Gastrite/duodenite"),("D97","Doença do fígado NE"),("D99","Outra doença digestiva"),
    # ── F: Olho
    ("F01","Olho vermelho"),("F02","Descarga do olho"),("F03","Visão turva/perturbada"),
    ("F05","Dor ocular"),("F70","Conjuntivite infecciosa"),("F71","Conjuntivite alérgica"),
    ("F82","Glaucoma"),("F83","Retinopatia"),("F85","Catarata"),("F91","Erros de refração"),
    ("F99","Outra doença ocular"),
    # ── H: Ouvido
    ("H01","Dor de ouvido"),("H02","Queixa auditiva"),("H03","Zumbido/tinido"),
    ("H04","Descarga do ouvido"),("H70","Otite externa infecciosa"),
    ("H71","Otite média aguda"),("H72","Otite media serosa"),
    ("H73","Otite media crónica"),("H80","Cera do ouvido"),
    ("H82","Síndrome vertiginosa"),("H83","Doença de Ménière"),
    ("H85","Presbiacusia"),("H86","Surdez"),("H99","Outra doença do ouvido"),
    # ── K: Circulatório
    ("K01","Dor cardíaca"),("K04","Palpitações/consciência do coração"),
    ("K05","Batimento irregular"),("K06","Varizes das pernas"),
    ("K07","Pernas inchadas/edema"),("K25","Medo de doença cardíaca"),
    ("K27","Medo de hipertensão"),("K29","Outros sintomas cardiovasculares"),
    ("K74","Flebite/tromboflebite"),("K75","Infarto agudo do miocárdio"),
    ("K76","Cardiopatia isquémica aguda NE"),("K77","Cardiopatia isquémica crónica"),
    ("K78","Taquicardia paroxística"),("K79","Fibrilação/flutter atrial"),
    ("K80","Arritmia cardíaca NE"),("K81","Insuficiência cardíaca"),
    ("K82","Acidente vascular cerebral NE"),("K83","AVC em recuperação/sequela"),
    ("K84","AIT/insuficiência vascular cerebral"),
    ("K86","Hipertensão não complicada"),("K87","Hipertensão com órgão-alvo atingido"),
    ("K88","Hipotensão postural"),("K90","Embolismo/trombose pulmonar"),
    ("K92","Aterosclerose/doença vascular periférica"),("K96","Hemorroidas"),
    ("K99","Outra doença cardiovascular"),
    # ── L: Locomotor
    ("L01","Dor no pescoço"),("L02","Dor nas costas"),("L03","Lombalgia"),
    ("L07","Dor no ombro"),("L08","Dor no cotovelo"),("L09","Dor no punho"),
    ("L10","Dor na mão/dedo"),("L11","Dor na anca"),("L12","Dor no joelho"),
    ("L13","Dor na perna/tornozelo"),("L14","Dor no pé/dedo do pé"),
    ("L15","Dor articular NE"),("L17","Fraqueza muscular"),("L18","Dor muscular"),
    ("L28","Limitação funcional locomotora"),("L29","Outros sintomas musculoesqueléticos"),
    ("L73","Fractura de vértebra"),("L74","Fractura de fémur"),
    ("L75","Fractura de pulso"),("L83","Síndrome do túnel cárpico"),
    ("L84","Epicondilite/tendinite cotovelo"),("L86","Síndrome lombociática"),
    ("L91","Osteoporose"),("L92","Artrite reumatoide"),
    ("L93","Artrose da anca"),("L94","Artrose do joelho"),("L95","Artrose NE"),
    ("L96","Artrite aguda NE"),("L97","Bursite/tendinite NE"),
    ("L99","Outra doença musculoesquelética"),
    # ── N: Neurológico
    ("N01","Cefaleia"),("N03","Dor facial"),("N04","Formigamento/parestesias"),
    ("N07","Convulsão/crise epilética"),("N08","Movimentos involuntários"),
    ("N17","Alterações da memória/concentração"),("N18","Paralisia/fraqueza"),
    ("N19","Fala/linguagem — problema"),("N27","Medo de doenças neurológicas"),
    ("N72","Herpes zóster"),("N75","Concussão"),("N76","Traumatismo crânio-encefálico"),
    ("N80","Cefaleia em salvas"),("N81","Enxaqueca"),("N82","Epilepsia"),
    ("N85","Esclerose múltipla"),("N86","Parkinson"),("N87","Demência"),
    ("N88","Neuralgia do trigêmeo"),("N89","Neuropatia periférica"),
    ("N90","Acidente isquêmico transitório"),("N91","Paralisia facial"),
    ("N92","Vertigens"),("N99","Outra doença neurológica"),
    # ── P: Psicológico
    ("P01","Sentimento de ansiedade/nervosismo"),("P02","Resposta aguda ao estresse"),
    ("P03","Sentimento de depressão"),("P06","Perturbações do sono"),
    ("P15","Abuso crónico de álcool"),("P16","Abuso agudo de álcool"),
    ("P17","Tabagismo"),("P18","Abuso de substâncias psicoativas"),
    ("P19","Abuso de drogas"),("P20","Perturbação da memória"),
    ("P21","Perturbação do sono"),("P22","Comportamento agitado/agressivo"),
    ("P24","Perturbações alimentares"),("P26","Medo de perturbação mental"),
    ("P29","Outros sintomas psicológicos"),("P70","Demência"),
    ("P71","Perturbação de uso de álcool"),("P72","Dependência de psicoativos"),
    ("P74","Perturbação de ansiedade"),("P75","Perturbação somatoforme"),
    ("P76","Perturbação depressiva"),("P77","Suicídio/tentativa de suicídio"),
    ("P78","Perturbação psicossomática"),("P79","Fobia/perturbação obsessivo-compulsiva"),
    ("P80","Perturbação de personalidade"),("P82","Perturbação pós-traumática de stress"),
    ("P86","Anorexia/bulimia nervosa"),("P98","Esquizofrenia"),
    ("P99","Outras perturbações psicológicas"),
    # ── R: Respiratório
    ("R02","Dispneia"),("R03","Pieira"),("R05","Tosse"),("R06","Hemorragia nasal"),
    ("R07","Espirros/obstrução nasal"),("R08","Sintomas dos seios paranasais"),
    ("R21","Sintomas da garganta"),("R25","Medo de doença respiratória"),
    ("R29","Outros sintomas respiratórios"),("R70","Gripe/influenza"),
    ("R71","Coqueluche"),("R72","Infecção respiratória aguda NE"),
    ("R73","Faringite/laringite aguda"),("R74","Infecção viral das vias aéreas"),
    ("R75","Rinite/coriza"),("R76","Amigdalite aguda"),
    ("R77","Laringite/traqueíte aguda"),("R78","Bronquite aguda"),
    ("R79","Bronquite crónica"),("R80","Gripe"),("R81","Pneumonia"),
    ("R82","Pleurisia/derrame pleural"),("R83","Infecção respiratória NE"),
    ("R84","Neoplasia maligna do brônquio/pulmão"),
    ("R88","Rinite alérgica"),("R89","Amigdalite crónica"),
    ("R91","Broncoespasmo"),("R92","Asma"),("R95","DPOC/bronquite crónica"),
    ("R99","Outra doença respiratória"),
    # ── S: Pele
    ("S01","Dor/sensibilidade da pele"),("S02","Comichão"),
    ("S03","Alterações da cor da pele"),("S05","Lesão cutânea NE"),
    ("S17","Ferida infectada"),("S25","Medo de câncer de pele"),
    ("S29","Outros sintomas de pele"),("S70","Herpes zóster"),
    ("S71","Herpes simplex"),("S72","Sarna/ácaros"),("S73","Pediculose"),
    ("S74","Dermatofitose"),("S75","Candidíase de pele"),
    ("S76","Outras infecções de pele NE"),("S77","Queimadura"),
    ("S78","Ferida traumática"),("S82","Dermatite seborreica"),
    ("S83","Dermatite atópica/eczema"),("S84","Urticária"),
    ("S85","Psoríase"),("S86","Acne"),("S87","Rosácea"),("S88","Verrugas"),
    ("S91","Cistos de pele"),("S97","Úlcera de pressão/escara"),
    ("S98","Úlcera de perna crónica"),("S99","Outra doença de pele"),
    # ── T: Endócrino
    ("T01","Sede excessiva"),("T02","Apetite aumentado"),("T03","Perda de apetite"),
    ("T07","Excesso de peso"),("T08","Perda de peso"),
    ("T27","Medo de diabetes"),("T29","Outros sintomas endócrinos/metabólicos"),
    ("T73","Obesidade"),("T74","Diabetes mellitus tipo 1"),
    ("T75","Diabetes mellitus tipo 2"),("T76","Hipoglicemia"),
    ("T78","Dislipidemia/hiperlipidemia"),("T80","Patologia da tireoide"),
    ("T81","Bócio"),("T82","Hipotireoidismo"),("T83","Hipertireoidismo"),
    ("T85","Hiperuricemia/gota"),("T87","Deficiência vitamínica/nutricional"),
    ("T99","Outra doença endócrina/metabólica"),
    # ── U: Urinário
    ("U01","Disúria/dor ao urinar"),("U02","Micção frequente"),
    ("U04","Incontinência urinária"),("U05","Retenção urinária"),
    ("U07","Sangue na urina"),("U27","Medo de doença urinária"),
    ("U29","Outros sintomas urinários"),("U70","Cistite/infecção urinária"),
    ("U71","Pielonefrite"),("U72","Uretrite"),
    ("U75","Neoplasia maligna do rim"),("U76","Neoplasia maligna da bexiga"),
    ("U79","Cálculo urinário"),("U80","Cálculo renal"),
    ("U88","Glomerulonefrite"),("U90","Síndrome nefrótico"),
    ("U95","Doença renal crónica"),("U99","Outra doença urinária"),
    # ── W: Gravidez
    ("W01","Questão de planejamento familiar"),("W02","Questão de esterilidade"),
    ("W05","Medo de gravidez"),("W11","Anticoncepção oral"),
    ("W12","Anticoncepção intrauterina"),("W13","Esterilização feminina"),
    ("W14","Anticoncepção NE"),("W17","Sangramento pós-coital"),
    ("W19","Sintoma pré-natal NE"),("W20","Queixa relacionada à gravidez"),
    ("W27","Medo de complicação da gravidez"),("W29","Outros sintomas de gravidez"),
    ("W70","Infecção puerperal"),("W71","Complicação infecciosa da gravidez"),
    ("W75","Lesão materna/fetal"),("W76","Hemorragia antes do parto"),
    ("W78","Gravidez"),("W79","Gravidez indesejada"),
    ("W80","Gravidez ectópica"),("W81","Toxemia/pré-eclampsia"),
    ("W82","Aborto"),("W83","Complicação pós-aborto"),
    ("W84","Gravidez de alto risco"),("W85","Diabetes gestacional"),
    ("W90","Parto normal"),("W91","Parto distócico"),
    ("W92","Complicação do parto"),("W93","Complicação do puerpério"),
    ("W94","Lactação/aleitamento"),("W99","Outra doença relacionada à gravidez"),
    # ── X: Genital Feminino
    ("X01","Dor menstrual/dismenorreia"),("X02","Dor pélvica"),
    ("X03","Sangramento intermenstrual"),("X04","Corrimento vaginal"),
    ("X07","Sintoma vaginal"),("X08","Sintoma de mama feminino"),
    ("X09","Nódulo/caroço da mama"),("X10","Dor na mama"),
    ("X11","Descarga da mama"),("X12","Irregularidade menstrual"),
    ("X13","Menopausa"),("X14","Amenorreia"),("X15","Menorragia"),
    ("X17","Sangramento pós-menopausa"),("X25","Medo de câncer genital feminino"),
    ("X27","Medo de câncer da mama"),("X29","Outros sintomas genitais femininos"),
    ("X70","Infecção genital feminina NE"),("X71","Sífilis genital feminina"),
    ("X72","Gonorreia genital feminina"),("X73","Tricomoníase vaginal"),
    ("X74","Candidíase vaginal"),("X75","Neoplasia maligna do colo do útero"),
    ("X76","Neoplasia maligna do útero"),("X77","Neoplasia maligna do ovário"),
    ("X78","Neoplasia maligna da mama"),("X79","Neoplasia benigna da mama"),
    ("X81","Vaginite/vulvite NE"),("X82","Doença inflamatória pélvica"),
    ("X85","Endometriose"),("X86","Prolapso genital feminino"),
    ("X87","Infertilidade feminina"),("X88","Menopausa/síndrome climatérico"),
    ("X89","Síndrome pré-menstrual"),("X99","Outra doença genital feminina"),
    # ── Y: Genital Masculino
    ("Y01","Dor no pénis"),("Y02","Dor escrotal"),("Y04","Outros sintomas penianos"),
    ("Y06","Disfunção erétil"),("Y16","Sintoma da próstata"),
    ("Y25","Medo de câncer genital masculino"),("Y29","Outros sintomas genitais masculinos"),
    ("Y70","Sífilis masculina"),("Y71","Gonorreia masculina"),
    ("Y72","Herpes genital masculino"),("Y73","Prostatite"),
    ("Y74","Neoplasia maligna da próstata"),("Y75","Neoplasia maligna do testículo"),
    ("Y81","Hiperplasia benigna da próstata"),("Y84","Orquite/epididimite"),
    ("Y85","Disfunção erétil"),("Y86","Infertilidade masculina"),
    ("Y99","Outra doença genital masculina"),
    # ── Z: Problemas Sociais
    ("Z01","Pobreza/problema financeiro"),("Z02","Problema alimentar/água"),
    ("Z03","Problema de habitação/vizinhança"),("Z04","Problema social/cultural"),
    ("Z05","Problema de trabalho"),("Z06","Problema de desemprego"),
    ("Z07","Problema educacional"),("Z08","Problema social NE"),
    ("Z09","Problema legal"),("Z10","Problema de sistema de saúde"),
    ("Z11","Problema de cumprimento do tratamento"),
    ("Z12","Problema com apoio social"),("Z13","Problema relacionado com o parceiro"),
    ("Z15","Perda/morte do parceiro"),("Z18","Doença/problema de saúde na família"),
    ("Z20","Problema de relacionamento com pais"),
    ("Z22","Abuso de criança/problema parental"),
    ("Z25","Problema de vida/relacionamento NE"),("Z29","Outros problemas sociais"),
    ("Z72","Problema de estilo de vida"),("Z73","Problema relacionado com violência"),
    ("Z75","Vítima de violência/abuso"),("Z76","Problema de cumprimento de tratamento"),
    ("Z99","Outro problema social"),
]


class CIAP2Etl(BaseETL):
    SOURCE_CODE = "CIAP2"

    def extract(self) -> list[dict]:
        logger.info(f"[CIAP2] {len(_CIAP2_CODES)} códigos no dataset")
        return [{"code": c, "name": n} for c, n in _CIAP2_CODES]

    def transform(self, raw: list[dict]) -> list[dict]:
        records = []
        for r in raw:
            code     = r["code"].strip()
            name     = r["name"].strip()
            cap      = code[0].upper()
            num      = int(code[1:]) if code[1:].isdigit() else 0
            cap_name = _CAPITULOS.get(cap, "Não especificado")
            comp     = _comp(num)

            info = {
                "capitulo":    cap_name,
                "componente":  comp,
                "fhir_system": "http://hl7.org/fhir/sid/icpc-2",
            }

            records.append({
                "code":              code,
                "name":              name,
                "description":       f"{cap_name} — {name}",
                "source":            "CIAP2",
                "category":          cap_name,
                "subcategory":       comp,
                "additional_info":   json.dumps(info, ensure_ascii=False),
                "official_url":      "https://sbmfc.org.br/ciap/",
                "source_competency": None,
                "last_updated":      None,
            })

        logger.info(f"[CIAP2] {len(records)} termos transformados")
        return records

    def load(self, records: list[dict]) -> int:
        deleted  = self.repo.delete_by_source("CIAP2")
        logger.info(f"[CIAP2] {deleted} registros anteriores removidos")
        inserted = self.repo.bulk_insert(records)
        self.repo.update_source_stats("CIAP2", len(records))
        logger.info(f"[CIAP2] {inserted} registros inseridos")
        return inserted
