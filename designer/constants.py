from cad.cases.case_model_base import CaseManufacturer
from config import CaseShape

CASE_SHAPE_OPTIONS = list(CaseShape)
MANUFACTURER_OPTIONS = [
    CaseManufacturer.GENERIC,
    CaseManufacturer.SPHERE_SAIDKOCC_100_MM,
    CaseManufacturer.SPHERE_PLAYTASTIC_120_MM,
]
MANUFACTURER_LABELS = {
    CaseManufacturer.GENERIC: "Generic",
    CaseManufacturer.SPHERE_SAIDKOCC_100_MM: "SaidKocc 100 mm",
    CaseManufacturer.SPHERE_PLAYTASTIC_120_MM: "Playtastic 120 mm",
}
