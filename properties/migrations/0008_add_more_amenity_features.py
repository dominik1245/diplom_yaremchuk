from django.db import migrations

FEATURES_TO_ADD = [
    chr(1052)+chr(1086)+chr(1078)+chr(1085)+chr(1072)+chr(32)+chr(1079)+chr(32)+chr(1090)+chr(1074)+chr(1072)+chr(1088)+chr(1080)+chr(1085)+chr(1072)+chr(1084)+chr(1080),
    chr(1041)+chr(1086)+chr(1081)+chr(1083)+chr(1077)+chr(1088),
    chr(1055)+chr(1088)+chr(1072)+chr(1083)+chr(1100)+chr(1085)+chr(1072)+chr(32)+chr(1084)+chr(1072)+chr(1096)+chr(1080)+chr(1085)+chr(1072),
    chr(1028)+chr(32)+chr(1088)+chr(1077)+chr(1079)+chr(1077)+chr(1088)+chr(1074)+chr(1085)+chr(1077)+chr(32)+chr(1078)+chr(1080)+chr(1074)+chr(1083)+chr(1077)+chr(1085)+chr(1085)+chr(1103),
    chr(1050)+chr(1086)+chr(1085)+chr(1076)+chr(1080)+chr(1094)+chr(1110)+chr(1086)+chr(1085)+chr(1077)+chr(1088),
    chr(1041)+chr(1072)+chr(1083)+chr(1082)+chr(1086)+chr(1085)+chr(47)+chr(1083)+chr(1086)+chr(1076)+chr(1078)+chr(1110)+chr(1103),
    chr(1055)+chr(1086)+chr(1089)+chr(1091)+chr(1076)+chr(1086)+chr(1084)+chr(1080)+chr(1081)+chr(1085)+chr(1072)+chr(32)+chr(1084)+chr(1072)+chr(1096)+chr(1080)+chr(1085)+chr(1072),
    chr(1042)+chr(1072)+chr(1085)+chr(1090)+chr(1072)+chr(1078)+chr(1085)+chr(1080)+chr(1081)+chr(32)+chr(1083)+chr(1110)+chr(1092)+chr(1090),
    chr(1062)+chr(1077)+chr(1085)+chr(1090)+chr(1088)+chr(1072)+chr(1083)+chr(1100)+chr(1085)+chr(1077)+chr(32)+chr(1086)+chr(1087)+chr(1072)+chr(1083)+chr(1077)+chr(1085)+chr(1085)+chr(1103),
    'Wi-Fi',
    chr(1061)+chr(1086)+chr(1083)+chr(1086)+chr(1076)+chr(1080)+chr(1083)+chr(1100)+chr(1085)+chr(1080)+chr(1082),
]
def add_features(apps,schema_editor):
    F=apps.get_model('properties','Feature')
    for n in FEATURES_TO_ADD: F.objects.get_or_create(name=n)
def noop(a,b): pass
class Migration(migrations.Migration):
    dependencies=[('properties','0007_add_featured_until_view_count_contact_verified')]
    operations=[migrations.RunPython(add_features,noop)]
