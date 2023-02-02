"""Module to test compressor scripts.

This module has been generated with the following code:

import ccp
import xlwings as xl
from pathlib import Path

ccp_path = Path(ccp.__file__).parent.parent
wb = xl.Book(ccp_path / "scripts/Performance-Test/Beta_1section.xlsm")
actual_test_sheet = wb.sheets["Actual Test Data"]

for row in range(45):
    for column in range(45):
        cell = actual_test_sheet.cells[row, column]
        if cell.value:
            if isinstance(cell.value, str):
                print(
                    f"assert actual_test_sheet[{cell.address}].value == {cell.value})"
                )
            elif isinstance(cell.value, (int, float)):
                print(
                    f"assert_allclose(actual_test_sheet[{cell.address}].value, {cell.value})"
                )

"""
import ccp
import xlwings as xl
from numpy.testing import assert_allclose
from pathlib import Path

ccp_path = Path(ccp.__file__).parent.parent
script_1sec = ccp_path / "scripts/Performance-Test/test_1sec.py"
beta_1section = ccp_path / "scripts/Performance-Test/Beta_1section.xlsm"


def test_1sec_reynolds_casing_balance_buffer():
    wb = xl.Book(beta_1section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$23"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$25"].value = "Yes"  # set casing
    actual_test_sheet["$C$35"].value = "Yes"  # set balance
    actual_test_sheet["$C$37"].value = "Yes"  # set buffer

    exec(open(str(script_1sec), encoding="utf-8").read(), {"__file__": __file__})

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$M$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$N$5"].value == "Mbal"
    assert actual_test_sheet["$O$5"].value == "Mbuf"
    assert actual_test_sheet["$P$5"].value == "Tbuf"
    assert actual_test_sheet["$Q$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$N$6"].value == "kg/s"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "degC"
    assert actual_test_sheet["$Q$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$N$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$11"].value, 9076.6)
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert actual_test_sheet["$F$19"].value == "Tested points - Results"
    assert actual_test_sheet["$G$20"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$20"].value == "Mach"
    assert actual_test_sheet["$K$20"].value == "Reynolds"
    assert actual_test_sheet["$M$20"].value == "Flow Coef."
    assert actual_test_sheet["$O$20"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$20"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$20"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$20"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$20"].value == "Power (kW)"
    assert actual_test_sheet["$Y$20"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$20"].value == "Polytropic Eff."
    assert actual_test_sheet["$G$21"].value == "vi/vd"
    assert actual_test_sheet["$H$21"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$21"].value == "Mt"
    assert actual_test_sheet["$J$21"].value == "Mt - Msp"
    assert actual_test_sheet["$K$21"].value == "Re_t"
    assert actual_test_sheet["$L$21"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$21"].value == "ft"
    assert actual_test_sheet["$N$21"].value == "ft/fsp"
    assert actual_test_sheet["$O$21"].value == "Pdconv"
    assert actual_test_sheet["$P$21"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$21"].value == "Ht"
    assert actual_test_sheet["$R$21"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$21"].value == "Hconv"
    assert actual_test_sheet["$T$21"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$21"].value == "Qconv"
    assert actual_test_sheet["$V$21"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$21"].value == "Wt"
    assert actual_test_sheet["$X$21"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$21"].value == "Wconv"
    assert actual_test_sheet["$Z$21"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$21"].value == "ht"
    assert actual_test_sheet["$AB$21"].value == "Reynolds corr."
    assert actual_test_sheet["$B$22"].value == "Opções"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 3.4559374329283625)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.160894764276381)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.8288430830451566)
    assert_allclose(actual_test_sheet["$J$22"].value, 0.010351151066870012)
    assert_allclose(actual_test_sheet["$K$22"].value, 1655358.1193824853)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.14492994025332448)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.07747213492591905)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$O$22"].value, 75.98584013761807)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.1495588523088969)
    assert_allclose(actual_test_sheet["$Q$22"].value, 77.9008162512784)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5835926991667765)
    assert_allclose(actual_test_sheet["$S$22"].value, 149.7166468647707)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.121599827300613)
    assert_allclose(actual_test_sheet["$U$22"].value, 9376.597450293692)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.8246352391512929)
    assert_allclose(actual_test_sheet["$W$22"].value, 897.0202174337649)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.09357159527324885)
    assert_allclose(actual_test_sheet["$Y$22"].value, 9169.10150307383)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.9564638992412829)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.8428296231306592)
    assert_allclose(actual_test_sheet["$AB$22"].value, 0.8447298011376306)

    assert actual_test_sheet["$B$23"].value == "Reynolds correction"
    assert actual_test_sheet["$C$23"].value == "Yes"
    assert actual_test_sheet["$D$23"].value == "Rugosidade [in]"
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 3.3740961743817475)
    assert_allclose(actual_test_sheet["$H$23"].value, 1.1334032108578198)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.8303249524396163)
    assert_allclose(actual_test_sheet["$J$23"].value, 0.011833020461329724)
    assert_allclose(actual_test_sheet["$K$23"].value, 1675777.4801777632)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.14671769645267466)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.08530597660420493)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$O$23"].value, 73.25679592304613)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.1082722529961593)
    assert_allclose(actual_test_sheet["$Q$23"].value, 75.6966911163375)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.5670805315323278)
    assert_allclose(actual_test_sheet["$S$23"].value, 145.24564501581557)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0881053895967134)
    assert_allclose(actual_test_sheet["$U$23"].value, 10325.324644000497)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.9080721020878842)
    assert_allclose(actual_test_sheet["$W$23"].value, 959.2134142436705)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.10005920450160574)
    assert_allclose(actual_test_sheet["$Y$23"].value, 9687.44007626271)
    assert_allclose(actual_test_sheet["$Z$23"].value, 1.0105337699557904)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.852443935100101)
    assert_allclose(actual_test_sheet["$AB$23"].value, 0.8541360235037936)
    assert_allclose(actual_test_sheet["$D$24"].value, 3.1496e-05)
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 3.18527134439569)
    assert_allclose(actual_test_sheet["$H$24"].value, 1.0699744709716206)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.8311500898089523)
    assert_allclose(actual_test_sheet["$J$24"].value, 0.012658157830665706)
    assert_allclose(actual_test_sheet["$K$24"].value, 1711274.130726835)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.1498254997630479)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.09321789046949196)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9924046063396693)
    assert_allclose(actual_test_sheet["$O$24"].value, 68.18412129334168)
    assert_allclose(actual_test_sheet["$P$24"].value, 1.0315298228947305)
    assert_allclose(actual_test_sheet["$Q$24"].value, 71.4252862665421)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5350813715044603)
    assert_allclose(actual_test_sheet["$S$24"].value, 136.9935210121865)
    assert_allclose(actual_test_sheet["$T$24"].value, 1.0262847367090384)
    assert_allclose(actual_test_sheet["$U$24"].value, 11283.223672824826)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9923155922136762)
    assert_allclose(actual_test_sheet["$W$24"].value, 1003.8778016545634)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.10471831686129819)
    assert_allclose(actual_test_sheet["$Y$24"].value, 9939.406905503827)
    assert_allclose(actual_test_sheet["$Z$24"].value, 1.0368173895552277)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.8564962734104754)
    assert_allclose(actual_test_sheet["$AB$24"].value, 0.8580290424765916)
    assert actual_test_sheet["$B$25"].value == "Casing heat loss"
    assert actual_test_sheet["$C$25"].value == "Yes"
    assert actual_test_sheet["$D$25"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.875006701574043)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9657525033052292)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.8366005347134757)
    assert_allclose(actual_test_sheet["$J$25"].value, 0.018108602735189105)
    assert_allclose(actual_test_sheet["$K$25"].value, 1789647.467606342)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.1566872433932648)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.10226088150818842)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.0886769626083173)
    assert_allclose(actual_test_sheet["$O$25"].value, 59.83049430443921)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9051511997645872)
    assert_allclose(actual_test_sheet["$Q$25"].value, 63.96183464190436)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.47916904492917206)
    assert_allclose(actual_test_sheet["$S$25"].value, 122.83390994646659)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.92020824048414)
    assert_allclose(actual_test_sheet["$U$25"].value, 12378.94029606622)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.0886796031929906)
    assert_allclose(actual_test_sheet["$W$25"].value, 1050.8829002444363)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.10962159771890664)
    assert_allclose(actual_test_sheet["$Y$25"].value, 10003.761709463935)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.043530484258123)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.8365916185883885)
    assert_allclose(actual_test_sheet["$AB$25"].value, 0.8386246799750752)
    assert_allclose(actual_test_sheet["$D$26"].value, 5.9719999999999995)
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 2.4430277206615076)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.8206450912205487)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.8418389096196611)
    assert_allclose(actual_test_sheet["$J$26"].value, 0.0233469776413745)
    assert_allclose(actual_test_sheet["$K$26"].value, 1889107.4210050653)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1653951628065291)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.10965222708314944)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.1673657782283218)
    assert_allclose(actual_test_sheet["$O$26"].value, 49.610801298444386)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.7505416232744991)
    assert_allclose(actual_test_sheet["$Q$26"].value, 54.27554019559298)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.4066043274734131)
    assert_allclose(actual_test_sheet["$S$26"].value, 103.28051784508978)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.7737243212720412)
    assert_allclose(actual_test_sheet["$U$26"].value, 13274.420900431114)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.1674336359058548)
    assert_allclose(actual_test_sheet["$W$26"].value, 1072.5770438320292)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.1118845964608808)
    assert_allclose(actual_test_sheet["$Y$26"].value, 9578.368956517868)
    assert_allclose(actual_test_sheet["$Z$26"].value, 0.999156146046753)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.7865213283384558)
    assert_allclose(actual_test_sheet["$AB$26"].value, 0.7897173176529169)
    assert actual_test_sheet["$D$27"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert_allclose(actual_test_sheet["$D$28"].value, 56.750000000000014)
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert actual_test_sheet["$D$29"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$30"].value, 13.420000000000016)
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert actual_test_sheet["$D$31"].value == "Heat Transfer Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$32"].value, 13.6)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 3.013470908784257)
    assert_allclose(actual_test_sheet["$H$32"].value, 1.0122644487063397)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.8184919319782866)
    assert_allclose(actual_test_sheet["$K$32"].value, 11421781.562105583)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.09393133594301997)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0000000000000002)
    assert_allclose(actual_test_sheet["$O$32"].value, 67.51797346880429)
    assert_allclose(actual_test_sheet["$P$32"].value, 1.0214519435522587)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 135.91123193054122)
    assert_allclose(actual_test_sheet["$T$32"].value, 1.0203628706338321)
    assert_allclose(actual_test_sheet["$U$32"].value, 11370.600000000002)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0000000000000002)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 9948.855905199256)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0378030507009344)

    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8570276292888267)
    assert actual_test_sheet["$B$33"].value == "Curve Shape"
    assert actual_test_sheet["$C$33"].value == "No"
    assert actual_test_sheet["$F$34"].value == "Status"
    assert actual_test_sheet["$AA$34"].value == "t - test condition (flange-flange)"
    assert actual_test_sheet["$B$35"].value == "Balance line leakage"
    assert actual_test_sheet["$C$35"].value == "Yes"
    assert (
        actual_test_sheet["$AA$35"].value
        == "conv - test converted condition (flange-flange)"
    )
    assert actual_test_sheet["$F$36"].value == "Calculado"
    assert (
        actual_test_sheet["$AA$36"].value
        == "sp - specified condition (flange-flange) - data sheet"
    )
    assert actual_test_sheet["$B$37"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$37"].value == "Yes"
    assert actual_test_sheet["$B$39"].value == "VSD"
    assert actual_test_sheet["$C$39"].value == "Yes"
    assert (
        actual_test_sheet["$D$42"].value
        == "*Casing Temperature is considered the mean of suction and discharge Temperature if no value is given."
    )


def test_1sec_reynolds_casing_balance():
    wb = xl.Book(beta_1section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$23"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$25"].value = "Yes"  # set casing
    actual_test_sheet["$C$35"].value = "Yes"  # set balance
    actual_test_sheet["$C$37"].value = "No"  # set buffer

    exec(open(str(script_1sec), encoding="utf-8").read(), {"__file__": __file__})

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$M$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$N$5"].value == "Mbal"
    assert actual_test_sheet["$O$5"].value == "Mbuf"
    assert actual_test_sheet["$P$5"].value == "Tbuf"
    assert actual_test_sheet["$Q$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$N$6"].value == "kg/s"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "degC"
    assert actual_test_sheet["$Q$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$N$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$11"].value, 9076.6)
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert actual_test_sheet["$F$19"].value == "Tested points - Results"
    assert actual_test_sheet["$G$20"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$20"].value == "Mach"
    assert actual_test_sheet["$K$20"].value == "Reynolds"
    assert actual_test_sheet["$M$20"].value == "Flow Coef."
    assert actual_test_sheet["$O$20"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$20"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$20"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$20"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$20"].value == "Power (kW)"
    assert actual_test_sheet["$Y$20"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$20"].value == "Polytropic Eff."
    assert actual_test_sheet["$G$21"].value == "vi/vd"
    assert actual_test_sheet["$H$21"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$21"].value == "Mt"
    assert actual_test_sheet["$J$21"].value == "Mt - Msp"
    assert actual_test_sheet["$K$21"].value == "Re_t"
    assert actual_test_sheet["$L$21"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$21"].value == "ft"
    assert actual_test_sheet["$N$21"].value == "ft/fsp"
    assert actual_test_sheet["$O$21"].value == "Pdconv"
    assert actual_test_sheet["$P$21"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$21"].value == "Ht"
    assert actual_test_sheet["$R$21"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$21"].value == "Hconv"
    assert actual_test_sheet["$T$21"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$21"].value == "Qconv"
    assert actual_test_sheet["$V$21"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$21"].value == "Wt"
    assert actual_test_sheet["$X$21"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$21"].value == "Wconv"
    assert actual_test_sheet["$Z$21"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$21"].value == "ht"
    assert actual_test_sheet["$AB$21"].value == "Reynolds corr."
    assert actual_test_sheet["$B$22"].value == "Opções"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 3.4559374329283625)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.160894764276381)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.8288430830451566)
    assert_allclose(actual_test_sheet["$J$22"].value, 0.010351151066870012)
    assert_allclose(actual_test_sheet["$K$22"].value, 1655358.1193824853)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.14492994025332448)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.07747213492591905)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$O$22"].value, 75.96056233108033)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.149176434660822)
    assert_allclose(actual_test_sheet["$Q$22"].value, 77.9008162512784)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5835926991667765)
    assert_allclose(actual_test_sheet["$S$22"].value, 149.68268000707954)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.1213453651381338)
    assert_allclose(actual_test_sheet["$U$22"].value, 9375.866988021484)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.8245709978384151)
    assert_allclose(actual_test_sheet["$W$22"].value, 897.0202174337649)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.09357159527324885)
    assert_allclose(actual_test_sheet["$Y$22"].value, 9168.026226106853)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.9563517330055558)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.8428296231306592)
    assert_allclose(actual_test_sheet["$AB$22"].value, 0.8445714062641103)
    assert actual_test_sheet["$B$23"].value == "Reynolds correction"
    assert actual_test_sheet["$C$23"].value == "Yes"
    assert actual_test_sheet["$D$23"].value == "Rugosidade [in]"
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 3.3740961743817475)

    assert_allclose(actual_test_sheet["$H$23"].value, 1.1334032108578198)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.8303249524396163)
    assert_allclose(actual_test_sheet["$J$23"].value, 0.011833020461329724)
    assert_allclose(actual_test_sheet["$K$23"].value, 1675777.4801777632)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.14671769645267466)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.08530597660420493)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$O$23"].value, 73.23466250833097)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.1079374055723294)
    assert_allclose(actual_test_sheet["$Q$23"].value, 75.6966911163375)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.5670805315323278)
    assert_allclose(actual_test_sheet["$S$23"].value, 145.2161098313247)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0878841272420057)
    assert_allclose(actual_test_sheet["$U$23"].value, 10324.593243134324)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.9080077782293215)
    assert_allclose(actual_test_sheet["$W$23"].value, 959.2134142436705)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.10005920450160574)
    assert_allclose(actual_test_sheet["$Y$23"].value, 9686.941439052693)
    assert_allclose(actual_test_sheet["$Z$23"].value, 1.010481755209303)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.852443935100101)
    assert_allclose(actual_test_sheet["$AB$23"].value, 0.8539458017918141)
    assert_allclose(actual_test_sheet["$D$24"].value, 3.1496e-05)
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 3.18527134439569)
    assert_allclose(actual_test_sheet["$H$24"].value, 1.0699744709716206)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.8311500898089523)
    assert_allclose(actual_test_sheet["$J$24"].value, 0.012658157830665706)
    assert_allclose(actual_test_sheet["$K$24"].value, 1711274.130726835)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.1498254997630479)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.09321789046949196)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9924046063396693)
    assert_allclose(actual_test_sheet["$O$24"].value, 68.16563659788666)
    assert_allclose(actual_test_sheet["$P$24"].value, 1.0312501754597074)
    assert_allclose(actual_test_sheet["$Q$24"].value, 71.4252862665421)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5350813715044603)
    assert_allclose(actual_test_sheet["$S$24"].value, 136.96848289428266)
    assert_allclose(actual_test_sheet["$T$24"].value, 1.0260971640555963)
    assert_allclose(actual_test_sheet["$U$24"].value, 11282.343270713336)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9922381642757054)
    assert_allclose(actual_test_sheet["$W$24"].value, 1003.8778016545634)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.10471831686129819)
    assert_allclose(actual_test_sheet["$Y$24"].value, 9939.504480969186)
    assert_allclose(actual_test_sheet["$Z$24"].value, 1.0368275680236454)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.8564962734104754)
    assert_allclose(actual_test_sheet["$AB$24"].value, 0.8577968630138084)
    assert actual_test_sheet["$B$25"].value == "Casing heat loss"
    assert actual_test_sheet["$C$25"].value == "Yes"
    assert actual_test_sheet["$D$25"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.875006701574043)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9657525033052292)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.8366005347134757)
    assert_allclose(actual_test_sheet["$J$25"].value, 0.018108602735189105)
    assert_allclose(actual_test_sheet["$K$25"].value, 1789647.467606342)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.1566872433932648)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.10226088150818842)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.0886769626083173)
    assert_allclose(actual_test_sheet["$O$25"].value, 59.811932406195666)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.904870384359995)
    assert_allclose(actual_test_sheet["$Q$25"].value, 63.96183464190436)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.47916904492917206)
    assert_allclose(actual_test_sheet["$S$25"].value, 122.80973137556435)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.920027107113094)
    assert_allclose(actual_test_sheet["$U$25"].value, 12378.01373068288)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.0885981153749915)
    assert_allclose(actual_test_sheet["$W$25"].value, 1050.8829002444363)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.10962159771890664)
    assert_allclose(actual_test_sheet["$Y$25"].value, 10006.969553600626)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.0438651066974218)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.8365916185883885)
    assert_allclose(actual_test_sheet["$AB$25"].value, 0.838128089329152)
    assert_allclose(actual_test_sheet["$D$26"].value, 5.9719999999999995)
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 2.4430277206615076)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.8206450912205487)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.8418389096196611)
    assert_allclose(actual_test_sheet["$J$26"].value, 0.0233469776413745)
    assert_allclose(actual_test_sheet["$K$26"].value, 1889107.4210050653)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1653951628065291)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.10965222708314944)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.1673657782283218)
    assert_allclose(actual_test_sheet["$O$26"].value, 49.593886000494905)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.7502857186156567)
    assert_allclose(actual_test_sheet["$Q$26"].value, 54.27554019559298)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.4066043274734131)
    assert_allclose(actual_test_sheet["$S$26"].value, 103.25744424837144)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.7735514657971395)
    assert_allclose(actual_test_sheet["$U$26"].value, 13273.126193974786)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.1673197715137975)
    assert_allclose(actual_test_sheet["$W$26"].value, 1072.5770438320292)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.1118845964608808)
    assert_allclose(actual_test_sheet["$Y$26"].value, 9585.400821012232)
    assert_allclose(actual_test_sheet["$Z$26"].value, 0.9998896666137311)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.7865213283384558)
    assert_allclose(actual_test_sheet["$AB$26"].value, 0.7888847303086017)
    assert actual_test_sheet["$D$27"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert_allclose(actual_test_sheet["$D$28"].value, 56.750000000000014)
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert actual_test_sheet["$D$29"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$30"].value, 13.420000000000016)
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert actual_test_sheet["$D$31"].value == "Heat Transfer Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$32"].value, 13.6)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 3.012312356663731)
    assert_allclose(actual_test_sheet["$H$32"].value, 1.011875275835892)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.8184919319782866)
    assert_allclose(actual_test_sheet["$K$32"].value, 11421781.562105583)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.09393133594301997)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0000000000000002)
    assert_allclose(actual_test_sheet["$O$32"].value, 67.49274211334662)
    assert_allclose(actual_test_sheet["$P$32"].value, 1.0210702286436706)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 135.87534497932174)
    assert_allclose(actual_test_sheet["$T$32"].value, 1.0200934468927294)
    assert_allclose(actual_test_sheet["$U$32"].value, 11370.600000000002)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0000000000000002)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 9949.279759595218)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0378472645672696)
    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8567648326906814)

    assert actual_test_sheet["$B$33"].value == "Curve Shape"
    assert actual_test_sheet["$C$33"].value == "No"
    assert actual_test_sheet["$F$34"].value == "Status"
    assert actual_test_sheet["$AA$34"].value == "t - test condition (flange-flange)"
    assert actual_test_sheet["$B$35"].value == "Balance line leakage"
    assert actual_test_sheet["$C$35"].value == "Yes"
    assert (
        actual_test_sheet["$AA$35"].value
        == "conv - test converted condition (flange-flange)"
    )
    assert actual_test_sheet["$F$36"].value == "Calculado"
    assert (
        actual_test_sheet["$AA$36"].value
        == "sp - specified condition (flange-flange) - data sheet"
    )
    assert actual_test_sheet["$B$37"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$37"].value == "No"
    assert actual_test_sheet["$B$39"].value == "VSD"
    assert actual_test_sheet["$C$39"].value == "Yes"
    assert (
        actual_test_sheet["$D$42"].value
        == "*Casing Temperature is considered the mean of suction and discharge Temperature if no value is given."
    )


def test_1sec_reynolds_casing():
    wb = xl.Book(beta_1section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$23"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$25"].value = "Yes"  # set casing
    actual_test_sheet["$C$35"].value = "No"  # set balance
    actual_test_sheet["$C$37"].value = "No"  # set buffer

    exec(open(str(script_1sec), encoding="utf-8").read(), {"__file__": __file__})

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$M$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$N$5"].value == "Mbal"
    assert actual_test_sheet["$O$5"].value == "Mbuf"
    assert actual_test_sheet["$P$5"].value == "Tbuf"
    assert actual_test_sheet["$Q$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$N$6"].value == "kg/s"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "degC"
    assert actual_test_sheet["$Q$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$N$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$11"].value, 9076.6)
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert actual_test_sheet["$F$19"].value == "Tested points - Results"
    assert actual_test_sheet["$G$20"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$20"].value == "Mach"
    assert actual_test_sheet["$K$20"].value == "Reynolds"
    assert actual_test_sheet["$M$20"].value == "Flow Coef."
    assert actual_test_sheet["$O$20"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$20"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$20"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$20"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$20"].value == "Power (kW)"
    assert actual_test_sheet["$Y$20"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$20"].value == "Polytropic Eff."
    assert actual_test_sheet["$G$21"].value == "vi/vd"
    assert actual_test_sheet["$H$21"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$21"].value == "Mt"
    assert actual_test_sheet["$J$21"].value == "Mt - Msp"
    assert actual_test_sheet["$K$21"].value == "Re_t"
    assert actual_test_sheet["$L$21"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$21"].value == "ft"
    assert actual_test_sheet["$N$21"].value == "ft/fsp"
    assert actual_test_sheet["$O$21"].value == "Pdconv"
    assert actual_test_sheet["$P$21"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$21"].value == "Ht"
    assert actual_test_sheet["$R$21"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$21"].value == "Hconv"
    assert actual_test_sheet["$T$21"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$21"].value == "Qconv"
    assert actual_test_sheet["$V$21"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$21"].value == "Wt"
    assert actual_test_sheet["$X$21"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$21"].value == "Wconv"
    assert actual_test_sheet["$Z$21"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$21"].value == "ht"
    assert actual_test_sheet["$AB$21"].value == "Reynolds corr."
    assert actual_test_sheet["$B$22"].value == "Opções"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 3.4559374329283625)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.160894764276381)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.8288430830451566)
    assert_allclose(actual_test_sheet["$J$22"].value, 0.010351151066870012)
    assert_allclose(actual_test_sheet["$K$22"].value, 1655358.1193824853)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.14492994025332448)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.07747213492591905)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$O$22"].value, 76.06781071455399)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.1507989518086836)
    assert_allclose(actual_test_sheet["$Q$22"].value, 77.9008162512784)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5835926991667765)
    assert_allclose(actual_test_sheet["$S$22"].value, 149.8077361685122)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.1222822213395183)
    assert_allclose(actual_test_sheet["$U$22"].value, 9378.176606825054)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$W$22"].value, 897.0202174337649)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.09357159527324885)
    assert_allclose(actual_test_sheet["$Y$22"].value, 9163.471705693537)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.9558766336348885)

    assert_allclose(actual_test_sheet["$AA$22"].value, 0.8428296231306592)
    assert_allclose(actual_test_sheet["$AB$22"].value, 0.8459054788691976)
    assert actual_test_sheet["$B$23"].value == "Reynolds correction"
    assert actual_test_sheet["$C$23"].value == "Yes"
    assert actual_test_sheet["$D$23"].value == "Rugosidade [in]"
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 3.3740961743817475)
    assert_allclose(actual_test_sheet["$H$23"].value, 1.1334032108578198)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.8303249524396163)
    assert_allclose(actual_test_sheet["$J$23"].value, 0.011833020461329724)
    assert_allclose(actual_test_sheet["$K$23"].value, 1675777.4801777632)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.14671769645267466)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.08530597660420493)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$O$23"].value, 73.32576127165949)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.1093156016892511)
    assert_allclose(actual_test_sheet["$Q$23"].value, 75.6966911163375)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.5670805315323278)
    assert_allclose(actual_test_sheet["$S$23"].value, 145.3224386228336)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0886806876558999)
    assert_allclose(actual_test_sheet["$U$23"].value, 10326.480804703724)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$W$23"].value, 959.2134142436705)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.10005920450160574)
    assert_allclose(actual_test_sheet["$Y$23"].value, 9680.476517008328)
    assert_allclose(actual_test_sheet["$Z$23"].value, 1.0098073745685423)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.852443935100101)
    assert_allclose(actual_test_sheet["$AB$23"].value, 0.8552981177154928)
    assert_allclose(actual_test_sheet["$D$24"].value, 3.1496e-05)
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 3.18527134439569)
    assert_allclose(actual_test_sheet["$H$24"].value, 1.0699744709716206)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.8311500898089523)
    assert_allclose(actual_test_sheet["$J$24"].value, 0.012658157830665706)
    assert_allclose(actual_test_sheet["$K$24"].value, 1711274.130726835)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.1498254997630479)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.09321789046949196)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9924046063396693)
    assert_allclose(actual_test_sheet["$O$24"].value, 68.23917121086298)
    assert_allclose(actual_test_sheet["$P$24"].value, 1.0323626506938424)
    assert_allclose(actual_test_sheet["$Q$24"].value, 71.4252862665421)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5350813715044603)
    assert_allclose(actual_test_sheet["$S$24"].value, 137.05622715293217)
    assert_allclose(actual_test_sheet["$T$24"].value, 1.0267544987435473)
    assert_allclose(actual_test_sheet["$U$24"].value, 11284.235816845845)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9924046063396694)
    assert_allclose(actual_test_sheet["$W$24"].value, 1003.8778016545634)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.10471831686129819)
    assert_allclose(actual_test_sheet["$Y$24"].value, 9931.100063889104)
    assert_allclose(actual_test_sheet["$Z$24"].value, 1.0359508712689447)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.8564962734104754)
    assert_allclose(actual_test_sheet["$AB$24"].value, 0.8592168810822384)
    assert actual_test_sheet["$B$25"].value == "Casing heat loss"
    assert actual_test_sheet["$C$25"].value == "Yes"
    assert actual_test_sheet["$D$25"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.875006701574043)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9657525033052292)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.8366005347134757)
    assert_allclose(actual_test_sheet["$J$25"].value, 0.018108602735189105)
    assert_allclose(actual_test_sheet["$K$25"].value, 1789647.467606342)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.1566872433932648)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.10226088150818842)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.0886769626083173)
    assert_allclose(actual_test_sheet["$O$25"].value, 59.866074683555176)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9056894808404717)
    assert_allclose(actual_test_sheet["$Q$25"].value, 63.96183464190436)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.47916904492917206)
    assert_allclose(actual_test_sheet["$S$25"].value, 122.88061645982015)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9205581415700124)
    assert_allclose(actual_test_sheet["$U$25"].value, 12378.91027103413)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.088676962608317)
    assert_allclose(actual_test_sheet["$W$25"].value, 1050.8829002444363)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.10962159771890664)
    assert_allclose(actual_test_sheet["$Y$25"].value, 9996.417020100047)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.0427643317375792)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.8365916185883885)
    assert_allclose(actual_test_sheet["$AB$25"].value, 0.8395579221216346)
    assert_allclose(actual_test_sheet["$D$26"].value, 5.9719999999999995)
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 2.4430277206615076)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.8206450912205487)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.8418389096196611)
    assert_allclose(actual_test_sheet["$J$26"].value, 0.0233469776413745)
    assert_allclose(actual_test_sheet["$K$26"].value, 1889107.4210050653)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1653951628065291)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.10965222708314944)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.1673657782283218)
    assert_allclose(actual_test_sheet["$O$26"].value, 49.62497703440796)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.7507560822149465)
    assert_allclose(actual_test_sheet["$Q$26"].value, 54.27554019559298)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.4066043274734131)
    assert_allclose(actual_test_sheet["$S$26"].value, 103.30347723850417)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.7738963211947469)
    assert_allclose(actual_test_sheet["$U$26"].value, 13273.649317922955)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.1673657782283215)
    assert_allclose(actual_test_sheet["$W$26"].value, 1072.5770438320292)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.1118845964608808)
    assert_allclose(actual_test_sheet["$Y$26"].value, 9574.151811208734)
    assert_allclose(actual_test_sheet["$Z$26"].value, 0.9987162395581304)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.7865213283384558)
    assert_allclose(actual_test_sheet["$AB$26"].value, 0.7901948653419568)
    assert actual_test_sheet["$D$27"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert_allclose(actual_test_sheet["$D$28"].value, 56.750000000000014)
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert actual_test_sheet["$D$29"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$30"].value, 13.420000000000016)
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert actual_test_sheet["$D$31"].value == "Heat Transfer Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$32"].value, 13.6)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 3.0168032199372132)
    assert_allclose(actual_test_sheet["$H$32"].value, 1.0133838157798136)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.8184919319782866)
    assert_allclose(actual_test_sheet["$K$32"].value, 11421781.562105583)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.09393133594301997)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0000000000000002)
    assert_allclose(actual_test_sheet["$O$32"].value, 67.57857696817732)
    assert_allclose(actual_test_sheet["$P$32"].value, 1.0223687892311244)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 135.9844156703325)
    assert_allclose(actual_test_sheet["$T$32"].value, 1.020912302566399)
    assert_allclose(actual_test_sheet["$U$32"].value, 11370.600000000002)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0000000000000002)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 9940.50388083594)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0369318192300625)

    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8582095740245056)
    assert actual_test_sheet["$B$33"].value == "Curve Shape"
    assert actual_test_sheet["$C$33"].value == "No"
    assert actual_test_sheet["$F$34"].value == "Status"
    assert actual_test_sheet["$AA$34"].value == "t - test condition (flange-flange)"
    assert actual_test_sheet["$B$35"].value == "Balance line leakage"
    assert actual_test_sheet["$C$35"].value == "No"
    assert (
        actual_test_sheet["$AA$35"].value
        == "conv - test converted condition (flange-flange)"
    )
    assert actual_test_sheet["$F$36"].value == "Calculado"
    assert (
        actual_test_sheet["$AA$36"].value
        == "sp - specified condition (flange-flange) - data sheet"
    )
    assert actual_test_sheet["$B$37"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$37"].value == "No"
    assert actual_test_sheet["$B$39"].value == "VSD"
    assert actual_test_sheet["$C$39"].value == "Yes"
    assert (
        actual_test_sheet["$D$42"].value
        == "*Casing Temperature is considered the mean of suction and discharge Temperature if no value is given."
    )

    wb = xl.Book(beta_1section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$23"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$25"].value = "Yes"  # set casing
    actual_test_sheet["$C$35"].value = "No"  # set balance
    actual_test_sheet["$C$37"].value = "No"  # set buffer

    exec(open(str(script_1sec), encoding="utf-8").read(), {"__file__": __file__})

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$M$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$N$5"].value == "Mbal"
    assert actual_test_sheet["$O$5"].value == "Mbuf"
    assert actual_test_sheet["$P$5"].value == "Tbuf"
    assert actual_test_sheet["$Q$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$N$6"].value == "kg/s"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "degC"
    assert actual_test_sheet["$Q$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$N$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$11"].value, 9076.6)
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert actual_test_sheet["$F$19"].value == "Tested points - Results"
    assert actual_test_sheet["$G$20"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$20"].value == "Mach"
    assert actual_test_sheet["$K$20"].value == "Reynolds"
    assert actual_test_sheet["$M$20"].value == "Flow Coef."
    assert actual_test_sheet["$O$20"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$20"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$20"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$20"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$20"].value == "Power (kW)"
    assert actual_test_sheet["$Y$20"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$20"].value == "Polytropic Eff."
    assert actual_test_sheet["$G$21"].value == "vi/vd"
    assert actual_test_sheet["$H$21"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$21"].value == "Mt"
    assert actual_test_sheet["$J$21"].value == "Mt - Msp"
    assert actual_test_sheet["$K$21"].value == "Re_t"
    assert actual_test_sheet["$L$21"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$21"].value == "ft"
    assert actual_test_sheet["$N$21"].value == "ft/fsp"
    assert actual_test_sheet["$O$21"].value == "Pdconv"
    assert actual_test_sheet["$P$21"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$21"].value == "Ht"
    assert actual_test_sheet["$R$21"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$21"].value == "Hconv"
    assert actual_test_sheet["$T$21"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$21"].value == "Qconv"
    assert actual_test_sheet["$V$21"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$21"].value == "Wt"
    assert actual_test_sheet["$X$21"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$21"].value == "Wconv"
    assert actual_test_sheet["$Z$21"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$21"].value == "ht"
    assert actual_test_sheet["$AB$21"].value == "Reynolds corr."
    assert actual_test_sheet["$B$22"].value == "Opções"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 3.4559374329283625)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.160894764276381)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.8288430830451566)
    assert_allclose(actual_test_sheet["$J$22"].value, 0.010351151066870012)
    assert_allclose(actual_test_sheet["$K$22"].value, 1655358.1193824853)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.14492994025332448)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.07747213492591905)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$O$22"].value, 76.06781071455399)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.1507989518086836)
    assert_allclose(actual_test_sheet["$Q$22"].value, 77.9008162512784)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5835926991667765)
    assert_allclose(actual_test_sheet["$S$22"].value, 149.8077361685122)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.1222822213395183)
    assert_allclose(actual_test_sheet["$U$22"].value, 9378.176606825054)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$W$22"].value, 897.0202174337649)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.09357159527324885)
    assert_allclose(actual_test_sheet["$Y$22"].value, 9163.471705693537)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.9558766336348885)

    assert_allclose(actual_test_sheet["$AA$22"].value, 0.8428296231306592)
    assert_allclose(actual_test_sheet["$AB$22"].value, 0.8459054788691976)
    assert actual_test_sheet["$B$23"].value == "Reynolds correction"
    assert actual_test_sheet["$C$23"].value == "Yes"
    assert actual_test_sheet["$D$23"].value == "Rugosidade [in]"
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 3.3740961743817475)
    assert_allclose(actual_test_sheet["$H$23"].value, 1.1334032108578198)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.8303249524396163)
    assert_allclose(actual_test_sheet["$J$23"].value, 0.011833020461329724)
    assert_allclose(actual_test_sheet["$K$23"].value, 1675777.4801777632)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.14671769645267466)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.08530597660420493)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$O$23"].value, 73.32576127165949)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.1093156016892511)
    assert_allclose(actual_test_sheet["$Q$23"].value, 75.6966911163375)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.5670805315323278)
    assert_allclose(actual_test_sheet["$S$23"].value, 145.3224386228336)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0886806876558999)
    assert_allclose(actual_test_sheet["$U$23"].value, 10326.480804703724)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$W$23"].value, 959.2134142436705)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.10005920450160574)
    assert_allclose(actual_test_sheet["$Y$23"].value, 9680.476517008328)
    assert_allclose(actual_test_sheet["$Z$23"].value, 1.0098073745685423)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.852443935100101)
    assert_allclose(actual_test_sheet["$AB$23"].value, 0.8552981177154928)
    assert_allclose(actual_test_sheet["$D$24"].value, 3.1496e-05)
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 3.18527134439569)
    assert_allclose(actual_test_sheet["$H$24"].value, 1.0699744709716206)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.8311500898089523)
    assert_allclose(actual_test_sheet["$J$24"].value, 0.012658157830665706)
    assert_allclose(actual_test_sheet["$K$24"].value, 1711274.130726835)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.1498254997630479)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.09321789046949196)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9924046063396693)
    assert_allclose(actual_test_sheet["$O$24"].value, 68.23917121086298)
    assert_allclose(actual_test_sheet["$P$24"].value, 1.0323626506938424)
    assert_allclose(actual_test_sheet["$Q$24"].value, 71.4252862665421)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5350813715044603)
    assert_allclose(actual_test_sheet["$S$24"].value, 137.05622715293217)
    assert_allclose(actual_test_sheet["$T$24"].value, 1.0267544987435473)
    assert_allclose(actual_test_sheet["$U$24"].value, 11284.235816845845)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9924046063396694)
    assert_allclose(actual_test_sheet["$W$24"].value, 1003.8778016545634)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.10471831686129819)
    assert_allclose(actual_test_sheet["$Y$24"].value, 9931.100063889104)
    assert_allclose(actual_test_sheet["$Z$24"].value, 1.0359508712689447)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.8564962734104754)
    assert_allclose(actual_test_sheet["$AB$24"].value, 0.8592168810822384)
    assert actual_test_sheet["$B$25"].value == "Casing heat loss"
    assert actual_test_sheet["$C$25"].value == "Yes"
    assert actual_test_sheet["$D$25"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.875006701574043)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9657525033052292)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.8366005347134757)
    assert_allclose(actual_test_sheet["$J$25"].value, 0.018108602735189105)
    assert_allclose(actual_test_sheet["$K$25"].value, 1789647.467606342)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.1566872433932648)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.10226088150818842)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.0886769626083173)
    assert_allclose(actual_test_sheet["$O$25"].value, 59.866074683555176)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9056894808404717)
    assert_allclose(actual_test_sheet["$Q$25"].value, 63.96183464190436)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.47916904492917206)
    assert_allclose(actual_test_sheet["$S$25"].value, 122.88061645982015)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9205581415700124)
    assert_allclose(actual_test_sheet["$U$25"].value, 12378.91027103413)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.088676962608317)
    assert_allclose(actual_test_sheet["$W$25"].value, 1050.8829002444363)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.10962159771890664)
    assert_allclose(actual_test_sheet["$Y$25"].value, 9996.417020100047)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.0427643317375792)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.8365916185883885)
    assert_allclose(actual_test_sheet["$AB$25"].value, 0.8395579221216346)
    assert_allclose(actual_test_sheet["$D$26"].value, 5.9719999999999995)
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 2.4430277206615076)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.8206450912205487)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.8418389096196611)
    assert_allclose(actual_test_sheet["$J$26"].value, 0.0233469776413745)
    assert_allclose(actual_test_sheet["$K$26"].value, 1889107.4210050653)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1653951628065291)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.10965222708314944)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.1673657782283218)
    assert_allclose(actual_test_sheet["$O$26"].value, 49.62497703440796)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.7507560822149465)
    assert_allclose(actual_test_sheet["$Q$26"].value, 54.27554019559298)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.4066043274734131)
    assert_allclose(actual_test_sheet["$S$26"].value, 103.30347723850417)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.7738963211947469)
    assert_allclose(actual_test_sheet["$U$26"].value, 13273.649317922955)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.1673657782283215)
    assert_allclose(actual_test_sheet["$W$26"].value, 1072.5770438320292)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.1118845964608808)
    assert_allclose(actual_test_sheet["$Y$26"].value, 9574.151811208734)
    assert_allclose(actual_test_sheet["$Z$26"].value, 0.9987162395581304)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.7865213283384558)
    assert_allclose(actual_test_sheet["$AB$26"].value, 0.7901948653419568)
    assert actual_test_sheet["$D$27"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert_allclose(actual_test_sheet["$D$28"].value, 56.750000000000014)
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert actual_test_sheet["$D$29"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$30"].value, 13.420000000000016)
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert actual_test_sheet["$D$31"].value == "Heat Transfer Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$32"].value, 13.6)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 3.0168032199372132)
    assert_allclose(actual_test_sheet["$H$32"].value, 1.0133838157798136)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.8184919319782866)
    assert_allclose(actual_test_sheet["$K$32"].value, 11421781.562105583)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.09393133594301997)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0000000000000002)
    assert_allclose(actual_test_sheet["$O$32"].value, 67.57857696817732)
    assert_allclose(actual_test_sheet["$P$32"].value, 1.0223687892311244)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 135.9844156703325)
    assert_allclose(actual_test_sheet["$T$32"].value, 1.020912302566399)
    assert_allclose(actual_test_sheet["$U$32"].value, 11370.600000000002)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0000000000000002)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 9940.50388083594)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0369318192300625)

    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8582095740245056)
    assert actual_test_sheet["$B$33"].value == "Curve Shape"
    assert actual_test_sheet["$C$33"].value == "No"
    assert actual_test_sheet["$F$34"].value == "Status"
    assert actual_test_sheet["$AA$34"].value == "t - test condition (flange-flange)"
    assert actual_test_sheet["$B$35"].value == "Balance line leakage"
    assert actual_test_sheet["$C$35"].value == "No"
    assert (
        actual_test_sheet["$AA$35"].value
        == "conv - test converted condition (flange-flange)"
    )
    assert actual_test_sheet["$F$36"].value == "Calculado"
    assert (
        actual_test_sheet["$AA$36"].value
        == "sp - specified condition (flange-flange) - data sheet"
    )
    assert actual_test_sheet["$B$37"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$37"].value == "No"
    assert actual_test_sheet["$B$39"].value == "VSD"
    assert actual_test_sheet["$C$39"].value == "Yes"
    assert (
        actual_test_sheet["$D$42"].value
        == "*Casing Temperature is considered the mean of suction and discharge Temperature if no value is given."
    )


def test_1sec_reynolds():
    wb = xl.Book(beta_1section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$23"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$25"].value = "No"  # set casing
    actual_test_sheet["$C$35"].value = "No"  # set balance
    actual_test_sheet["$C$37"].value = "No"  # set buffer

    exec(open(str(script_1sec), encoding="utf-8").read(), {"__file__": __file__})

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$M$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$N$5"].value == "Mbal"
    assert actual_test_sheet["$O$5"].value == "Mbuf"
    assert actual_test_sheet["$P$5"].value == "Tbuf"
    assert actual_test_sheet["$Q$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$N$6"].value == "kg/s"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "degC"
    assert actual_test_sheet["$Q$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$N$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$11"].value, 9076.6)
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert actual_test_sheet["$F$19"].value == "Tested points - Results"
    assert actual_test_sheet["$G$20"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$20"].value == "Mach"
    assert actual_test_sheet["$K$20"].value == "Reynolds"
    assert actual_test_sheet["$M$20"].value == "Flow Coef."
    assert actual_test_sheet["$O$20"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$20"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$20"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$20"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$20"].value == "Power (kW)"
    assert actual_test_sheet["$Y$20"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$20"].value == "Polytropic Eff."
    assert actual_test_sheet["$G$21"].value == "vi/vd"
    assert actual_test_sheet["$H$21"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$21"].value == "Mt"
    assert actual_test_sheet["$J$21"].value == "Mt - Msp"
    assert actual_test_sheet["$K$21"].value == "Re_t"
    assert actual_test_sheet["$L$21"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$21"].value == "ft"
    assert actual_test_sheet["$N$21"].value == "ft/fsp"
    assert actual_test_sheet["$O$21"].value == "Pdconv"
    assert actual_test_sheet["$P$21"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$21"].value == "Ht"
    assert actual_test_sheet["$R$21"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$21"].value == "Hconv"
    assert actual_test_sheet["$T$21"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$21"].value == "Qconv"
    assert actual_test_sheet["$V$21"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$21"].value == "Wt"
    assert actual_test_sheet["$X$21"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$21"].value == "Wconv"
    assert actual_test_sheet["$Z$21"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$21"].value == "ht"
    assert actual_test_sheet["$AB$21"].value == "Reynolds corr."
    assert actual_test_sheet["$B$22"].value == "Opções"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 3.4559374329283625)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.160894764276381)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.8288430830451566)
    assert_allclose(actual_test_sheet["$J$22"].value, 0.010351151066870012)
    assert_allclose(actual_test_sheet["$K$22"].value, 1655358.1193824853)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.14492994025332448)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.07747213492591905)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$O$22"].value, 76.1199719006142)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.1515880771651166)
    assert_allclose(actual_test_sheet["$Q$22"].value, 77.9008162512784)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5835926991667765)
    assert_allclose(actual_test_sheet["$S$22"].value, 149.79413886272908)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.1221803573441813)
    assert_allclose(actual_test_sheet["$U$22"].value, 9378.176606825054)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$W$22"].value, 893.5009894977647)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.09320449120390714)
    assert_allclose(actual_test_sheet["$Y$22"].value, 9127.521183073572)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.9521264976991781)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.8461492720061206)
    assert_allclose(actual_test_sheet["$AB$22"].value, 0.8491601615466753)
    assert actual_test_sheet["$B$23"].value == "Reynolds correction"
    assert actual_test_sheet["$C$23"].value == "Yes"
    assert actual_test_sheet["$D$23"].value == "Rugosidade [in]"

    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 3.3740961743817475)
    assert_allclose(actual_test_sheet["$H$23"].value, 1.1334032108578198)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.8303249524396163)
    assert_allclose(actual_test_sheet["$J$23"].value, 0.011833020461329724)
    assert_allclose(actual_test_sheet["$K$23"].value, 1675777.4801777632)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.14671769645267466)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.08530597660420493)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$O$23"].value, 73.37038883424678)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.109990753922039)
    assert_allclose(actual_test_sheet["$Q$23"].value, 75.6966911163375)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.5670805315323278)
    assert_allclose(actual_test_sheet["$S$23"].value, 145.31038071350727)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.088590356024106)
    assert_allclose(actual_test_sheet["$U$23"].value, 10326.480804703724)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$W$23"].value, 955.6941863076705)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.09969210043226405)
    assert_allclose(actual_test_sheet["$Y$23"].value, 9644.960121087925)
    assert_allclose(actual_test_sheet["$Z$23"].value, 1.0061025240422787)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.855582956508056)
    assert_allclose(actual_test_sheet["$AB$23"].value, 0.8583764209107677)
    assert_allclose(actual_test_sheet["$D$24"].value, 3.1496e-05)
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 3.18527134439569)
    assert_allclose(actual_test_sheet["$H$24"].value, 1.0699744709716206)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.8311500898089523)
    assert_allclose(actual_test_sheet["$J$24"].value, 0.012658157830665706)
    assert_allclose(actual_test_sheet["$K$24"].value, 1711274.130726835)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.1498254997630479)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.09321789046949196)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9924046063396693)
    assert_allclose(actual_test_sheet["$O$24"].value, 68.27521139792962)
    assert_allclose(actual_test_sheet["$P$24"].value, 1.0329078880170897)
    assert_allclose(actual_test_sheet["$Q$24"].value, 71.4252862665421)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5350813715044603)
    assert_allclose(actual_test_sheet["$S$24"].value, 137.04562570318078)
    assert_allclose(actual_test_sheet["$T$24"].value, 1.0266750781549934)
    assert_allclose(actual_test_sheet["$U$24"].value, 11284.235816845845)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9924046063396694)
    assert_allclose(actual_test_sheet["$W$24"].value, 1000.3585737185633)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.1043512127919565)
    assert_allclose(actual_test_sheet["$Y$24"].value, 9896.285263997677)
    assert_allclose(actual_test_sheet["$Z$24"].value, 1.0323192068965636)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.8595093985954394)
    assert_allclose(actual_test_sheet["$AB$24"].value, 0.8621728820951834)
    assert actual_test_sheet["$B$25"].value == "Casing heat loss"
    assert actual_test_sheet["$C$25"].value == "No"
    assert actual_test_sheet["$D$25"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.875006701574043)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9657525033052292)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.8366005347134757)
    assert_allclose(actual_test_sheet["$J$25"].value, 0.018108602735189105)
    assert_allclose(actual_test_sheet["$K$25"].value, 1789647.467606342)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.1566872433932648)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.10226088150818842)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.0886769626083173)
    assert_allclose(actual_test_sheet["$O$25"].value, 59.89157140599735)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9060752103781747)
    assert_allclose(actual_test_sheet["$Q$25"].value, 63.96183464190436)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.47916904492917206)
    assert_allclose(actual_test_sheet["$S$25"].value, 122.87171897906819)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9204914862375309)
    assert_allclose(actual_test_sheet["$U$25"].value, 12378.91027103413)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.088676962608317)
    assert_allclose(actual_test_sheet["$W$25"].value, 1047.3636723084364)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.10925449364956497)
    assert_allclose(actual_test_sheet["$Y$25"].value, 9962.940721238523)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.0392722915054446)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.8394026351177957)
    assert_allclose(actual_test_sheet["$AB$25"].value, 0.8423179111066135)
    assert_allclose(actual_test_sheet["$D$26"].value, 5.9719999999999995)
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 2.4430277206615076)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.8206450912205487)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.8418389096196611)
    assert_allclose(actual_test_sheet["$J$26"].value, 0.0233469776413745)
    assert_allclose(actual_test_sheet["$K$26"].value, 1889107.4210050653)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1653951628065291)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.10965222708314944)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.1673657782283218)
    assert_allclose(actual_test_sheet["$O$26"].value, 49.64079438383467)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.750995376457408)
    assert_allclose(actual_test_sheet["$Q$26"].value, 54.27554019559298)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.4066043274734131)
    assert_allclose(actual_test_sheet["$S$26"].value, 103.29609599296704)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.7738410247137405)
    assert_allclose(actual_test_sheet["$U$26"].value, 13273.649317922955)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.1673657782283215)
    assert_allclose(actual_test_sheet["$W$26"].value, 1069.057815896029)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.11151749239153909)
    assert_allclose(actual_test_sheet["$Y$26"].value, 9542.738102784462)
    assert_allclose(actual_test_sheet["$Z$26"].value, 0.9954393559900909)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.789110475332932)
    assert_allclose(actual_test_sheet["$AB$26"].value, 0.7927394583315295)
    assert actual_test_sheet["$D$27"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert_allclose(actual_test_sheet["$D$28"].value, 56.750000000000014)
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert actual_test_sheet["$D$29"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$30"].value, 13.420000000000016)
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert actual_test_sheet["$D$31"].value == "Heat Transfer Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$32"].value, 13.6)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 3.0209838168138066)
    assert_allclose(actual_test_sheet["$H$32"].value, 1.0147881331668547)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.8184919319782866)
    assert_allclose(actual_test_sheet["$K$32"].value, 11421781.562105583)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.09393133594301997)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0000000000000002)
    assert_allclose(actual_test_sheet["$O$32"].value, 67.61378533012333)
    assert_allclose(actual_test_sheet["$P$32"].value, 1.0229014422106406)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 135.97404008824668)
    assert_allclose(actual_test_sheet["$T$32"].value, 1.020834407174155)
    assert_allclose(actual_test_sheet["$U$32"].value, 11370.600000000002)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0000000000000002)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 9905.765521922756)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0333081287072552)
    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8611535035908718)

    assert actual_test_sheet["$B$33"].value == "Curve Shape"
    assert actual_test_sheet["$C$33"].value == "No"
    assert actual_test_sheet["$F$34"].value == "Status"
    assert actual_test_sheet["$AA$34"].value == "t - test condition (flange-flange)"
    assert actual_test_sheet["$B$35"].value == "Balance line leakage"
    assert actual_test_sheet["$C$35"].value == "No"
    assert (
        actual_test_sheet["$AA$35"].value
        == "conv - test converted condition (flange-flange)"
    )
    assert actual_test_sheet["$F$36"].value == "Calculado"
    assert (
        actual_test_sheet["$AA$36"].value
        == "sp - specified condition (flange-flange) - data sheet"
    )
    assert actual_test_sheet["$B$37"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$37"].value == "No"
    assert actual_test_sheet["$B$39"].value == "VSD"
    assert actual_test_sheet["$C$39"].value == "Yes"
    assert (
        actual_test_sheet["$D$42"].value
        == "*Casing Temperature is considered the mean of suction and discharge Temperature if no value is given."
    )


def test_1sec():
    wb = xl.Book(beta_1section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$23"].value = "No"  # set reynolds
    actual_test_sheet["$C$25"].value = "No"  # set casing
    actual_test_sheet["$C$35"].value = "No"  # set balance
    actual_test_sheet["$C$37"].value = "No"  # set buffer

    exec(open(str(script_1sec), encoding="utf-8").read(), {"__file__": __file__})

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$M$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$N$5"].value == "Mbal"
    assert actual_test_sheet["$O$5"].value == "Mbuf"
    assert actual_test_sheet["$P$5"].value == "Tbuf"
    assert actual_test_sheet["$Q$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$N$6"].value == "kg/s"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "degC"
    assert actual_test_sheet["$Q$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$N$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$N$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$N$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$P$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$Q$11"].value, 9076.6)
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert actual_test_sheet["$F$19"].value == "Tested points - Results"
    assert actual_test_sheet["$G$20"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$20"].value == "Mach"
    assert actual_test_sheet["$K$20"].value == "Reynolds"
    assert actual_test_sheet["$M$20"].value == "Flow Coef."
    assert actual_test_sheet["$O$20"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$20"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$20"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$20"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$20"].value == "Power (kW)"
    assert actual_test_sheet["$Y$20"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$20"].value == "Polytropic Eff."
    assert actual_test_sheet["$G$21"].value == "vi/vd"
    assert actual_test_sheet["$H$21"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$21"].value == "Mt"
    assert actual_test_sheet["$J$21"].value == "Mt - Msp"
    assert actual_test_sheet["$K$21"].value == "Re_t"
    assert actual_test_sheet["$L$21"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$21"].value == "ft"
    assert actual_test_sheet["$N$21"].value == "ft/fsp"
    assert actual_test_sheet["$O$21"].value == "Pdconv"
    assert actual_test_sheet["$P$21"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$21"].value == "Ht"
    assert actual_test_sheet["$R$21"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$21"].value == "Hconv"
    assert actual_test_sheet["$T$21"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$21"].value == "Qconv"
    assert actual_test_sheet["$V$21"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$21"].value == "Wt"
    assert actual_test_sheet["$X$21"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$21"].value == "Wconv"
    assert actual_test_sheet["$Z$21"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$21"].value == "ht"
    assert actual_test_sheet["$AB$21"].value == "Reynolds corr."
    assert actual_test_sheet["$B$22"].value == "Opções"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 3.4559374329283625)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.160894764276381)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.8288430830451566)
    assert_allclose(actual_test_sheet["$J$22"].value, 0.010351151066870012)
    assert_allclose(actual_test_sheet["$K$22"].value, 1655358.1193824853)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.14492994025332448)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.07747213492591905)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$O$22"].value, 75.71494014977453)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.1454605166380414)
    assert_allclose(actual_test_sheet["$Q$22"].value, 77.9008162512784)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5835926991667765)
    assert_allclose(actual_test_sheet["$S$22"].value, 149.26300984397753)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.1182014129303102)
    assert_allclose(actual_test_sheet["$U$22"].value, 9378.176606825054)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$W$22"].value, 893.5009894977647)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.09320449120390714)
    assert_allclose(actual_test_sheet["$Y$22"].value, 9127.521183073572)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.9521264976991781)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.8461492720061206)
    assert actual_test_sheet["$B$23"].value == "Reynolds correction"
    assert actual_test_sheet["$C$23"].value == "No"
    assert actual_test_sheet["$D$23"].value == "Rugosidade [in]"
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 3.3740961743817475)
    assert_allclose(actual_test_sheet["$H$23"].value, 1.1334032108578198)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.8303249524396163)
    assert_allclose(actual_test_sheet["$J$23"].value, 0.011833020461329724)

    assert_allclose(actual_test_sheet["$K$23"].value, 1675777.4801777632)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.14671769645267466)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.08530597660420493)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$O$23"].value, 73.02053476483698)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.104697954082254)
    assert_allclose(actual_test_sheet["$Q$23"].value, 75.6966911163375)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.5670805315323278)
    assert_allclose(actual_test_sheet["$S$23"].value, 144.83748867535252)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.085047693004106)
    assert_allclose(actual_test_sheet["$U$23"].value, 10326.480804703724)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$W$23"].value, 955.6941863076705)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.09969210043226405)
    assert_allclose(actual_test_sheet["$Y$23"].value, 9644.960121087925)
    assert_allclose(actual_test_sheet["$Z$23"].value, 1.0061025240422787)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.855582956508056)
    assert_allclose(actual_test_sheet["$D$24"].value, 3.1496e-05)
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 3.18527134439569)
    assert_allclose(actual_test_sheet["$H$24"].value, 1.0699744709716206)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.8311500898089523)
    assert_allclose(actual_test_sheet["$J$24"].value, 0.012658157830665706)
    assert_allclose(actual_test_sheet["$K$24"].value, 1711274.130726835)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.1498254997630479)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.09321789046949196)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9924046063396693)
    assert_allclose(actual_test_sheet["$O$24"].value, 67.9810303589998)
    assert_allclose(actual_test_sheet["$P$24"].value, 1.0284573427987869)
    assert_allclose(actual_test_sheet["$Q$24"].value, 71.4252862665421)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5350813715044603)
    assert_allclose(actual_test_sheet["$S$24"].value, 136.62225497311204)
    assert_allclose(actual_test_sheet["$T$24"].value, 1.0235034032098678)
    assert_allclose(actual_test_sheet["$U$24"].value, 11284.235816845845)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9924046063396694)
    assert_allclose(actual_test_sheet["$W$24"].value, 1000.3585737185633)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.1043512127919565)
    assert_allclose(actual_test_sheet["$Y$24"].value, 9896.285263997675)
    assert_allclose(actual_test_sheet["$Z$24"].value, 1.0323192068965636)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.8595093985954394)
    assert actual_test_sheet["$B$25"].value == "Casing heat loss"
    assert actual_test_sheet["$C$25"].value == "No"
    assert actual_test_sheet["$D$25"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.875006701574043)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9657525033052292)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.8366005347134757)
    assert_allclose(actual_test_sheet["$J$25"].value, 0.018108602735189105)
    assert_allclose(actual_test_sheet["$K$25"].value, 1789647.467606342)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.1566872433932648)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.10226088150818842)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.0886769626083173)
    assert_allclose(actual_test_sheet["$O$25"].value, 59.6294738041809)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9021100424233117)
    assert_allclose(actual_test_sheet["$Q$25"].value, 63.96183464190436)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.47916904492917206)
    assert_allclose(actual_test_sheet["$S$25"].value, 122.44645796213116)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9173056502390458)
    assert_allclose(actual_test_sheet["$U$25"].value, 12378.91027103413)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.088676962608317)
    assert_allclose(actual_test_sheet["$W$25"].value, 1047.3636723084364)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.10925449364956497)
    assert_allclose(actual_test_sheet["$Y$25"].value, 9962.940721238523)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.0392722915054446)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.8394026351177957)
    assert_allclose(actual_test_sheet["$D$26"].value, 5.9719999999999995)
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 2.4430277206615076)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.8206450912205487)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.8418389096196611)
    assert_allclose(actual_test_sheet["$J$26"].value, 0.0233469776413745)
    assert_allclose(actual_test_sheet["$K$26"].value, 1889107.4210050653)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1653951628065291)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.10965222708314944)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.1673657782283218)
    assert_allclose(actual_test_sheet["$O$26"].value, 49.396311049498706)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.7472966875869699)
    assert_allclose(actual_test_sheet["$Q$26"].value, 54.27554019559298)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.4066043274734131)
    assert_allclose(actual_test_sheet["$S$26"].value, 102.82322969966397)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.7702985545608786)
    assert_allclose(actual_test_sheet["$U$26"].value, 13273.649317922955)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.1673657782283215)
    assert_allclose(actual_test_sheet["$W$26"].value, 1069.057815896029)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.11151749239153909)
    assert_allclose(actual_test_sheet["$Y$26"].value, 9542.738102784462)
    assert_allclose(actual_test_sheet["$Z$26"].value, 0.9954393559900909)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.789110475332932)
    assert actual_test_sheet["$D$27"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert_allclose(actual_test_sheet["$D$28"].value, 56.750000000000014)
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert actual_test_sheet["$D$29"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$30"].value, 13.420000000000016)
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert actual_test_sheet["$D$31"].value == "Heat Transfer Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$32"].value, 13.6)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 3.0079433194146583)
    assert_allclose(actual_test_sheet["$H$32"].value, 1.0104076588532895)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.8184919319782866)
    assert_allclose(actual_test_sheet["$K$32"].value, 11421781.562105583)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.09393133594301997)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0000000000000002)
    assert_allclose(actual_test_sheet["$O$32"].value, 67.32213550933648)
    assert_allclose(actual_test_sheet["$P$32"].value, 1.0184891907615201)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 135.55060300573808)
    assert_allclose(actual_test_sheet["$T$32"].value, 1.0176554243122964)
    assert_allclose(actual_test_sheet["$U$32"].value, 11370.600000000002)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0000000000000002)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 9905.770518277424)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0333086498960398)
    assert_allclose(actual_test_sheet["$AA$32"].value, 0.8584713504085514)
    assert actual_test_sheet["$B$33"].value == "Curve Shape"
    assert actual_test_sheet["$C$33"].value == "No"

    assert actual_test_sheet["$F$34"].value == "Status"
    assert actual_test_sheet["$AA$34"].value == "t - test condition (flange-flange)"
    assert actual_test_sheet["$B$35"].value == "Balance line leakage"
    assert actual_test_sheet["$C$35"].value == "No"
    assert (
        actual_test_sheet["$AA$35"].value
        == "conv - test converted condition (flange-flange)"
    )
    assert actual_test_sheet["$F$36"].value == "Calculado"
    assert (
        actual_test_sheet["$AA$36"].value
        == "sp - specified condition (flange-flange) - data sheet"
    )
    assert actual_test_sheet["$B$37"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$37"].value == "No"
    assert actual_test_sheet["$B$39"].value == "VSD"
    assert actual_test_sheet["$C$39"].value == "Yes"
    assert (
        actual_test_sheet["$D$42"].value
        == "*Casing Temperature is considered the mean of suction and discharge Temperature if no value is given."
    )
