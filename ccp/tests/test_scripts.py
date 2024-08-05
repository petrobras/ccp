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
                    f"assert actual_test_sheet['{cell.address}'].value == '{cell.value}'"
                )
            elif isinstance(cell.value, (int, float)):
                print(
                    f"assert_allclose(actual_test_sheet['{cell.address}'].value, {cell.value})"
                )

"""

import ccp
from numpy.testing import assert_allclose
from pathlib import Path
import runpy
import pytest

xlwings = pytest.importorskip("xlwings")  # skip if xlwings not installed or linux


ccp_path = Path(ccp.__file__).parent.parent
script_1sec = ccp_path / "scripts/Performance-Test/test_1sec.py"
beta_1section = ccp_path / "scripts/Performance-Test/Beta_1section.xlsm"
script_2sec = ccp_path / "scripts/Performance-Test/test_2sec_back.py"
beta_2section = ccp_path / "scripts/Performance-Test/Beta_2section_back_to_back.xlsm"


def test_1sec_reynolds_casing_balance_buffer():
    wb = xl.Book(beta_1section)
    wb.app.visible = True
    data_sheet = wb.sheets["DataSheet"]
    data_sheet["$T$38"].value = 12493  # set speed
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$23"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$25"].value = "Yes"  # set casing
    actual_test_sheet["$C$35"].value = "Yes"  # set balance
    actual_test_sheet["$C$37"].value = "Yes"  # set buffer

    runpy.run_path(str(script_1sec), run_name="test_script")

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$N$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$M$5"].value == "Casing DeltaT"
    assert actual_test_sheet["$O$5"].value == "Mbal"
    assert actual_test_sheet["$P$5"].value == "Mbuf"
    assert actual_test_sheet["$Q$5"].value == "Tbuf"
    assert actual_test_sheet["$R$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$M$6"].value == "degC"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "kg/s"
    assert actual_test_sheet["$Q$6"].value == "degC"
    assert actual_test_sheet["$R$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$P$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$P$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$P$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$P$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$P$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$11"].value, 9076.6)
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
    assert_allclose(actual_test_sheet["$O$22"].value, 76.23853434704401)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.1533817601670804)
    assert_allclose(actual_test_sheet["$Q$22"].value, 77.9008162512784)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5835926991667765)
    assert_allclose(actual_test_sheet["$S$22"].value, 150.0480046948712)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.124082189100708)
    assert_allclose(actual_test_sheet["$U$22"].value, 9376.20169357603)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.8246004338888036)
    assert_allclose(actual_test_sheet["$W$22"].value, 897.0202174337649)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.09357159527324885)
    assert_allclose(actual_test_sheet["$Y$22"].value, 9168.980228928654)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.9564512486733147)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.8428296231306592)
    assert_allclose(actual_test_sheet["$AB$22"].value, 0.8465748498789616)

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
    assert_allclose(actual_test_sheet["$O$23"].value, 73.47621923597612)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.1115918190011516)
    assert_allclose(actual_test_sheet["$Q$23"].value, 75.6966911163375)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.5670805315323278)
    assert_allclose(actual_test_sheet["$S$23"].value, 145.54217786361806)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0903268606077805)
    assert_allclose(actual_test_sheet["$U$23"].value, 10324.99454036504)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.9080430707583628)
    assert_allclose(actual_test_sheet["$W$23"].value, 959.2134142436705)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.10005920450160574)
    assert_allclose(actual_test_sheet["$Y$23"].value, 9687.345746574252)
    assert_allclose(actual_test_sheet["$Z$23"].value, 1.0105239300667233)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.852443935100101)
    assert_allclose(actual_test_sheet["$AB$23"].value, 0.8558607947837948)
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
    assert_allclose(actual_test_sheet["$O$24"].value, 68.36993738584523)
    assert_allclose(actual_test_sheet["$P$24"].value, 1.0343409589386572)
    assert_allclose(actual_test_sheet["$Q$24"].value, 71.4252862665421)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5350813715044603)
    assert_allclose(actual_test_sheet["$S$24"].value, 137.26082063450787)
    assert_allclose(actual_test_sheet["$T$24"].value, 1.0282872074864127)
    assert_allclose(actual_test_sheet["$U$24"].value, 11282.954037237723)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9922918788135826)
    assert_allclose(actual_test_sheet["$W$24"].value, 1003.8778016545634)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.10471831686129819)
    assert_allclose(actual_test_sheet["$Y$24"].value, 9939.337698190362)
    assert_allclose(actual_test_sheet["$Z$24"].value, 1.0368101702767771)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.8564962734104754)
    assert_allclose(actual_test_sheet["$AB$24"].value, 0.8596886569540688)
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
    assert_allclose(actual_test_sheet["$O$25"].value, 59.99637739967156)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9076607776047135)
    assert_allclose(actual_test_sheet["$Q$25"].value, 63.96183464190436)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.47916904492917206)
    assert_allclose(actual_test_sheet["$S$25"].value, 123.10281820408775)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9222227623267246)
    assert_allclose(actual_test_sheet["$U$25"].value, 12378.651737534648)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.0886542255936054)
    assert_allclose(actual_test_sheet["$W$25"].value, 1050.8829002444363)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.10962159771890664)
    assert_allclose(actual_test_sheet["$Y$25"].value, 10003.732701838719)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.043527458362258)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.8365916185883885)
    assert_allclose(actual_test_sheet["$AB$25"].value, 0.8404434444176646)
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
    assert_allclose(actual_test_sheet["$O$26"].value, 49.76749283926639)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.7529121458285385)
    assert_allclose(actual_test_sheet["$Q$26"].value, 54.27554019559298)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.4066043274734131)
    assert_allclose(actual_test_sheet["$S$26"].value, 103.58285437453814)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.7759892704698564)
    assert_allclose(actual_test_sheet["$U$26"].value, 13274.174959729891)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.1674120063787214)
    assert_allclose(actual_test_sheet["$W$26"].value, 1072.5770438320292)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.1118845964608808)
    assert_allclose(actual_test_sheet["$Y$26"].value, 9578.351531737124)
    assert_allclose(actual_test_sheet["$Z$26"].value, 0.9991543284015095)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.7865213283384558)
    assert_allclose(actual_test_sheet["$AB$26"].value, 0.7920158502546781)
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
    assert_allclose(actual_test_sheet["$G$32"].value, 3.0216086680043603)
    assert_allclose(actual_test_sheet["$H$32"].value, 1.0149980288867988)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.8184919319782866)
    assert_allclose(actual_test_sheet["$K$32"].value, 11421781.562105583)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.09393133594301997)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0000000000000002)
    assert_allclose(actual_test_sheet["$O$32"].value, 67.70012788771723)
    assert_allclose(actual_test_sheet["$P$32"].value, 1.0242076836265845)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 136.1752343482896)
    assert_allclose(actual_test_sheet["$T$32"].value, 1.0223448868439837)
    assert_allclose(actual_test_sheet["$U$32"].value, 11370.600000000002)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0000000000000002)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 9948.81476586312)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0377987593000986)
    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8586959237603171)

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
    assert actual_test_sheet["$B$39"].value == "Variable Speed"
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

    runpy.run_path(str(script_1sec), run_name="test_script")

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$N$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$M$5"].value == "Casing DeltaT"
    assert actual_test_sheet["$O$5"].value == "Mbal"
    assert actual_test_sheet["$P$5"].value == "Mbuf"
    assert actual_test_sheet["$Q$5"].value == "Tbuf"
    assert actual_test_sheet["$R$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$M$6"].value == "degC"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "kg/s"
    assert actual_test_sheet["$Q$6"].value == "degC"
    assert actual_test_sheet["$R$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$P$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$P$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$P$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$P$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$P$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$11"].value, 9076.6)
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
    assert_allclose(actual_test_sheet["$O$22"].value, 76.20429982343441)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.1528638399914435)
    assert_allclose(actual_test_sheet["$Q$22"].value, 77.9008162512784)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5835926991667765)
    assert_allclose(actual_test_sheet["$S$22"].value, 150.00273307524557)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.1237430374978834)
    assert_allclose(actual_test_sheet["$U$22"].value, 9375.277564585342)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.8245191603420524)
    assert_allclose(actual_test_sheet["$W$22"].value, 897.0202174337649)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.09357159527324885)
    assert_allclose(actual_test_sheet["$Y$22"].value, 9167.845863963377)

    assert_allclose(actual_test_sheet["$Z$22"].value, 0.9563329187434423)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.8428296231306592)
    assert_allclose(actual_test_sheet["$AB$22"].value, 0.8463407193074675)
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
    assert_allclose(actual_test_sheet["$O$23"].value, 73.4467931498535)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.1111466437194177)
    assert_allclose(actual_test_sheet["$Q$23"].value, 75.6966911163375)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.5670805315323278)
    assert_allclose(actual_test_sheet["$S$23"].value, 145.50313307542726)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0900343572114723)
    assert_allclose(actual_test_sheet["$U$23"].value, 10324.089946088505)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.9079635152136655)
    assert_allclose(actual_test_sheet["$W$23"].value, 959.2134142436705)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.10005920450160574)
    assert_allclose(actual_test_sheet["$Y$23"].value, 9686.79778457121)
    assert_allclose(actual_test_sheet["$Z$23"].value, 1.0104667700632168)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.852443935100101)
    assert_allclose(actual_test_sheet["$AB$23"].value, 0.8556046253075776)
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
    assert_allclose(actual_test_sheet["$O$24"].value, 68.3459128845979)
    assert_allclose(actual_test_sheet["$P$24"].value, 1.033977502036277)
    assert_allclose(actual_test_sheet["$Q$24"].value, 71.4252862665421)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5350813715044603)
    assert_allclose(actual_test_sheet["$S$24"].value, 137.22808114226774)
    assert_allclose(actual_test_sheet["$T$24"].value, 1.028041940112267)
    assert_allclose(actual_test_sheet["$U$24"].value, 11281.917461432098)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9922007160072553)
    assert_allclose(actual_test_sheet["$W$24"].value, 1003.8778016545634)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.10471831686129819)
    assert_allclose(actual_test_sheet["$Y$24"].value, 9939.395283904678)
    assert_allclose(actual_test_sheet["$Z$24"].value, 1.0368161772619584)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.8564962734104754)
    assert_allclose(actual_test_sheet["$AB$24"].value, 0.8593996630553393)
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
    assert_allclose(actual_test_sheet["$O$25"].value, 59.97420897210316)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9073254004856758)
    assert_allclose(actual_test_sheet["$Q$25"].value, 63.96183464190436)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.47916904492917206)
    assert_allclose(actual_test_sheet["$S$25"].value, 123.0729839674153)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9219992596274577)
    assert_allclose(actual_test_sheet["$U$25"].value, 12377.574367591586)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.0885594751017171)
    assert_allclose(actual_test_sheet["$W$25"].value, 1050.8829002444363)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.10962159771890664)
    assert_allclose(actual_test_sheet["$Y$25"].value, 10006.87236511171)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.0438549685959908)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.8365916185883885)
    assert_allclose(actual_test_sheet["$AB$25"].value, 0.8399030283809681)
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
    assert_allclose(actual_test_sheet["$O$26"].value, 49.74827737894513)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.7526214429492456)
    assert_allclose(actual_test_sheet["$Q$26"].value, 54.27554019559298)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.4066043274734131)
    assert_allclose(actual_test_sheet["$S$26"].value, 103.55562523956195)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.7757852838476177)
    assert_allclose(actual_test_sheet["$U$26"].value, 13272.702430467198)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.167282503163175)
    assert_allclose(actual_test_sheet["$W$26"].value, 1072.5770438320292)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.1118845964608808)
    assert_allclose(actual_test_sheet["$Y$26"].value, 9585.371332121695)
    assert_allclose(actual_test_sheet["$Z$26"].value, 0.9998865905152478)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.7865213283384558)
    assert_allclose(actual_test_sheet["$AB$26"].value, 0.7911400017807817)
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
    assert_allclose(actual_test_sheet["$G$32"].value, 3.020157673135021)
    assert_allclose(actual_test_sheet["$H$32"].value, 1.0145106206569048)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.8184919319782866)
    assert_allclose(actual_test_sheet["$K$32"].value, 11421781.562105583)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.09393133594301997)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0000000000000002)
    assert_allclose(actual_test_sheet["$O$32"].value, 67.66830664588834)
    assert_allclose(actual_test_sheet["$P$32"].value, 1.0237262730089007)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 136.12985988581008)
    assert_allclose(actual_test_sheet["$T$32"].value, 1.0220042349631095)
    assert_allclose(actual_test_sheet["$U$32"].value, 11370.600000000002)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0000000000000002)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 9949.214351566803)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0378404416067126)
    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8583753248481422)

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
    assert actual_test_sheet["$B$39"].value == "Variable Speed"
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

    runpy.run_path(str(script_1sec), run_name="test_script")

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$N$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$M$5"].value == "Casing DeltaT"
    assert actual_test_sheet["$O$5"].value == "Mbal"
    assert actual_test_sheet["$P$5"].value == "Mbuf"
    assert actual_test_sheet["$Q$5"].value == "Tbuf"
    assert actual_test_sheet["$R$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$M$6"].value == "degC"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "kg/s"
    assert actual_test_sheet["$Q$6"].value == "degC"
    assert actual_test_sheet["$R$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$P$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$P$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$P$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$P$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$P$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$11"].value, 9076.6)
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
    assert_allclose(actual_test_sheet["$O$22"].value, 76.33811700415067)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.1548883056603734)
    assert_allclose(actual_test_sheet["$Q$22"].value, 77.9008162512784)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5835926991667765)
    assert_allclose(actual_test_sheet["$S$22"].value, 150.16108163960803)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.1249293031948613)
    assert_allclose(actual_test_sheet["$U$22"].value, 9378.176606825054)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.8247741198199791)
    assert_allclose(actual_test_sheet["$W$22"].value, 897.0202174337649)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.09357159527324885)
    assert_allclose(actual_test_sheet["$Y$22"].value, 9163.471705693537)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.9558766336348885)

    assert_allclose(actual_test_sheet["$AA$22"].value, 0.8428296231306592)
    assert_allclose(actual_test_sheet["$AB$22"].value, 0.8479006820381271)
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
    assert_allclose(actual_test_sheet["$O$23"].value, 73.55896116151546)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.1128435879200524)
    assert_allclose(actual_test_sheet["$Q$23"].value, 75.6966911163375)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.5670805315323278)
    assert_allclose(actual_test_sheet["$S$23"].value, 145.6367621609612)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0910354373344635)
    assert_allclose(actual_test_sheet["$U$23"].value, 10326.480804703724)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.9081737819203669)
    assert_allclose(actual_test_sheet["$W$23"].value, 959.2134142436705)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.10005920450160574)
    assert_allclose(actual_test_sheet["$Y$23"].value, 9680.476517008334)
    assert_allclose(actual_test_sheet["$Z$23"].value, 1.0098073745685427)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.852443935100101)
    assert_allclose(actual_test_sheet["$AB$23"].value, 0.8571480751829137)
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
    assert_allclose(actual_test_sheet["$O$24"].value, 68.43486382296163)
    assert_allclose(actual_test_sheet["$P$24"].value, 1.0353232045833833)
    assert_allclose(actual_test_sheet["$Q$24"].value, 71.4252862665421)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5350813715044603)
    assert_allclose(actual_test_sheet["$S$24"].value, 137.33713370798657)
    assert_allclose(actual_test_sheet["$T$24"].value, 1.0288589056363973)
    assert_allclose(actual_test_sheet["$U$24"].value, 11284.235816845845)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9924046063396694)
    assert_allclose(actual_test_sheet["$W$24"].value, 1003.8778016545634)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.10471831686129819)
    assert_allclose(actual_test_sheet["$Y$24"].value, 9931.100063889104)
    assert_allclose(actual_test_sheet["$Z$24"].value, 1.0359508712689447)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.8564962734104754)
    assert_allclose(actual_test_sheet["$AB$24"].value, 0.860977907626768)
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
    assert_allclose(actual_test_sheet["$O$25"].value, 60.039273979698194)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9083097425067806)
    assert_allclose(actual_test_sheet["$Q$25"].value, 63.96183464190436)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.47916904492917206)
    assert_allclose(actual_test_sheet["$S$25"].value, 123.16085340692877)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9226575321058169)
    assert_allclose(actual_test_sheet["$U$25"].value, 12378.91027103413)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.088676962608317)
    assert_allclose(actual_test_sheet["$W$25"].value, 1050.8829002444363)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.10962159771890664)
    assert_allclose(actual_test_sheet["$Y$25"].value, 9996.417020100045)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.0427643317375792)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.8365916185883885)
    assert_allclose(actual_test_sheet["$AB$25"].value, 0.8414725865804766)
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
    assert_allclose(actual_test_sheet["$O$26"].value, 49.785262731381806)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.7531809792947324)
    assert_allclose(actual_test_sheet["$Q$26"].value, 54.27554019559298)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.4066043274734131)
    assert_allclose(actual_test_sheet["$S$26"].value, 103.61243616955963)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.7762108820065969)
    assert_allclose(actual_test_sheet["$U$26"].value, 13273.649317922955)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.1673657782283215)
    assert_allclose(actual_test_sheet["$W$26"].value, 1072.5770438320292)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.1118845964608808)
    assert_allclose(actual_test_sheet["$Y$26"].value, 9574.151811208734)
    assert_allclose(actual_test_sheet["$Z$26"].value, 0.9987162395581304)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.7865213283384558)
    assert_allclose(actual_test_sheet["$AB$26"].value, 0.7925581716647238)
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
    assert_allclose(actual_test_sheet["$G$32"].value, 3.0254650830034784)
    assert_allclose(actual_test_sheet["$H$32"].value, 1.0162934493243034)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.8184919319782866)
    assert_allclose(actual_test_sheet["$K$32"].value, 11421781.562105583)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.09393133594301997)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0000000000000002)
    assert_allclose(actual_test_sheet["$O$32"].value, 67.77249497335836)
    assert_allclose(actual_test_sheet["$P$32"].value, 1.0253024958148014)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 136.26522983057848)
    assert_allclose(actual_test_sheet["$T$32"].value, 1.0230205340833471)
    assert_allclose(actual_test_sheet["$U$32"].value, 11370.600000000002)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0000000000000002)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 9940.50029699479)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0369314453859426)
    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8599821268676723)

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
    assert actual_test_sheet["$B$39"].value == "Variable Speed"
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

    runpy.run_path(str(script_1sec), run_name="test_script")

    assert actual_test_sheet["$F$3"].value == "Tested points - Measurements"
    assert actual_test_sheet["$N$4"].value == "Gas Selection"
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$M$5"].value == "Casing DeltaT"
    assert actual_test_sheet["$O$5"].value == "Mbal"
    assert actual_test_sheet["$P$5"].value == "Mbuf"
    assert actual_test_sheet["$Q$5"].value == "Tbuf"
    assert actual_test_sheet["$R$5"].value == "Speed"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$M$6"].value == "degC"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "kg/s"
    assert actual_test_sheet["$Q$6"].value == "degC"
    assert actual_test_sheet["$R$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 9.7051)
    assert_allclose(actual_test_sheet["$H$7"].value, 6775.062621434255)
    assert_allclose(actual_test_sheet["$I$7"].value, 2.2762)
    assert_allclose(actual_test_sheet["$J$7"].value, 291.01)
    assert_allclose(actual_test_sheet["$K$7"].value, 10.45)
    assert_allclose(actual_test_sheet["$L$7"].value, 387.68)
    assert_allclose(actual_test_sheet["$M$7"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$7"].value, 3.0)
    assert_allclose(actual_test_sheet["$O$7"].value, 0.13491)
    assert_allclose(actual_test_sheet["$P$7"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$7"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$7"].value, 9025.3)
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 10.802)
    assert_allclose(actual_test_sheet["$H$8"].value, 7465.352120048199)
    assert_allclose(actual_test_sheet["$I$8"].value, 2.2943)
    assert_allclose(actual_test_sheet["$J$8"].value, 290.59)
    assert_allclose(actual_test_sheet["$K$8"].value, 10.192)
    assert_allclose(actual_test_sheet["$L$8"].value, 383.75)
    assert_allclose(actual_test_sheet["$M$8"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$O$8"].value, 0.1299)
    assert_allclose(actual_test_sheet["$P$8"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$8"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$8"].value, 9031.6)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 12.038000000000002)
    assert_allclose(actual_test_sheet["$H$9"].value, 8159.009215846355)
    assert_allclose(actual_test_sheet["$I$9"].value, 2.3354)
    assert_allclose(actual_test_sheet["$J$9"].value, 290.14)
    assert_allclose(actual_test_sheet["$K$9"].value, 9.6599)
    assert_allclose(actual_test_sheet["$L$9"].value, 377.94)
    assert_allclose(actual_test_sheet["$M$9"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$9"].value, 2.0)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.12324)
    assert_allclose(actual_test_sheet["$P$9"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$9"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$9"].value, 9033.0)
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 13.745068936568224)
    assert_allclose(actual_test_sheet["$H$10"].value, 8946.841792223522)
    assert_allclose(actual_test_sheet["$I$10"].value, 2.4024)
    assert_allclose(actual_test_sheet["$J$10"].value, 289.54)
    assert_allclose(actual_test_sheet["$K$10"].value, 8.8091)
    assert_allclose(actual_test_sheet["$L$10"].value, 370.41)
    assert_allclose(actual_test_sheet["$M$10"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$10"].value, 0.12943)
    assert_allclose(actual_test_sheet["$P$10"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$10"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$10"].value, 9029.3)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 15.543)
    assert_allclose(actual_test_sheet["$H$11"].value, 9643.768942532579)
    assert_allclose(actual_test_sheet["$I$11"].value, 2.5152)
    assert_allclose(actual_test_sheet["$J$11"].value, 289.08)
    assert_allclose(actual_test_sheet["$K$11"].value, 7.6823)
    assert_allclose(actual_test_sheet["$L$11"].value, 362.23)
    assert_allclose(actual_test_sheet["$M$11"].value, 43.33)
    assert_allclose(actual_test_sheet["$N$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$11"].value, 0.11104)
    assert_allclose(actual_test_sheet["$P$11"].value, 0.1)
    assert_allclose(actual_test_sheet["$Q$11"].value, 20.0)
    assert_allclose(actual_test_sheet["$R$11"].value, 9076.6)
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
    assert actual_test_sheet["$B$39"].value == "Variable Speed"
    assert actual_test_sheet["$C$39"].value == "Yes"
    assert (
        actual_test_sheet["$D$42"].value
        == "*Casing Temperature is considered the mean of suction and discharge Temperature if no value is given."
    )


def test_2sec_reynolds_casing_balance_divwall_buffer():
    wb = xl.Book(beta_2section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$4"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$8"].value = "Yes"  # set casing
    actual_test_sheet["$C$16"].value = "Yes"  # set casing
    actual_test_sheet["$C$26"].value = "Yes"  # set balance and divwall
    actual_test_sheet["$C$28"].value = "Yes"  # set buffer

    runpy.run_path(str(script_2sec), run_name="test_script")

    assert actual_test_sheet["$B$3"].value == "Opções"
    assert actual_test_sheet["$F$3"].value == "SECTION 1 - Tested points - Measurements"
    assert actual_test_sheet["$X$3"].value == "Ordenar por:"
    assert actual_test_sheet["$Y$3"].value == "Vazão Seção 1"
    assert (
        actual_test_sheet["$AD$3"].value == "SECTION 2 - Tested points - Measurements"
    )
    assert actual_test_sheet["$B$4"].value == "Reynolds correction"
    assert actual_test_sheet["$C$4"].value == "Yes"
    assert actual_test_sheet["$D$4"].value == "Rugosidade [in] - Case 1"
    assert actual_test_sheet["$G$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$H$4"].value, 3774.0)
    assert actual_test_sheet["$I$4"].value == "rpm"
    assert actual_test_sheet["$AE$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$AF$4"].value, 3774.0)
    assert actual_test_sheet["$AG$4"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$5"].value, 0.01)
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$M$5"].value == "Mbuf"
    assert actual_test_sheet["$N$5"].value == "Tbuf"
    assert actual_test_sheet["$O$5"].value == "Mbal"
    assert actual_test_sheet["$P$5"].value == "Pend"
    assert actual_test_sheet["$Q$5"].value == "Tend"
    assert actual_test_sheet["$R$5"].value == "Mdiv"
    assert actual_test_sheet["$S$5"].value == "Pdiv"
    assert actual_test_sheet["$T$5"].value == "Tdiv"
    assert actual_test_sheet["$U$5"].value == "Md1f"
    assert actual_test_sheet["$V$5"].value == "Gas Selection"
    assert actual_test_sheet["$W$5"].value == "Speed"
    assert actual_test_sheet["$AE$5"].value == "Ms"
    assert actual_test_sheet["$AF$5"].value == "Qs"
    assert actual_test_sheet["$AG$5"].value == "Ps"
    assert actual_test_sheet["$AH$5"].value == "Ts"
    assert actual_test_sheet["$AI$5"].value == "Pd"
    assert actual_test_sheet["$AJ$5"].value == "Td"
    assert actual_test_sheet["$AK$5"].value == "Mbal"
    assert actual_test_sheet["$AL$5"].value == "Mbuf"
    assert actual_test_sheet["$AM$5"].value == "Gas Selection"
    assert actual_test_sheet["$AN$5"].value == "Speed"
    assert actual_test_sheet["$D$6"].value == "Rugosidade [in] - Case 2"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$M$6"].value == "kg/s"
    assert actual_test_sheet["$N$6"].value == "kelvin"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "bar"
    assert actual_test_sheet["$Q$6"].value == "kelvin"
    assert actual_test_sheet["$R$6"].value == "kg/h"
    assert actual_test_sheet["$S$6"].value == "bar"
    assert actual_test_sheet["$T$6"].value == "kelvin"
    assert actual_test_sheet["$U$6"].value == "kg/s"
    assert actual_test_sheet["$W$6"].value == "rpm"
    assert actual_test_sheet["$AE$6"].value == "kg/s"
    assert actual_test_sheet["$AF$6"].value == "m³/h"
    assert actual_test_sheet["$AG$6"].value == "bar"
    assert actual_test_sheet["$AH$6"].value == "kelvin"
    assert actual_test_sheet["$AI$6"].value == "bar"
    assert actual_test_sheet["$AJ$6"].value == "kelvin"
    assert actual_test_sheet["$AK$6"].value == "kg/s"
    assert actual_test_sheet["$AL$6"].value == "kg/s"
    assert actual_test_sheet["$AN$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$7"].value, 0.01)
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 3.277)
    assert_allclose(actual_test_sheet["$H$7"].value, 1298.3249050526144)
    assert_allclose(actual_test_sheet["$I$7"].value, 5.038)
    assert_allclose(actual_test_sheet["$J$7"].value, 300.9)
    assert_allclose(actual_test_sheet["$K$7"].value, 15.04)
    assert_allclose(actual_test_sheet["$L$7"].value, 404.3)
    assert_allclose(actual_test_sheet["$M$7"].value, 0.06143)
    assert_allclose(actual_test_sheet["$N$7"].value, 301.0)
    assert_allclose(actual_test_sheet["$P$7"].value, 14.6)
    assert_allclose(actual_test_sheet["$Q$7"].value, 304.8)
    assert_allclose(actual_test_sheet["$S$7"].value, 26.27)
    assert_allclose(actual_test_sheet["$T$7"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$7"].value, 9123.0)
    assert actual_test_sheet["$Z$7"].value == "Status"
    assert_allclose(actual_test_sheet["$AD$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AE$7"].value, 2.075)
    assert_allclose(actual_test_sheet["$AF$7"].value, 322.5064631506056)
    assert_allclose(actual_test_sheet["$AG$7"].value, 12.52)
    assert_allclose(actual_test_sheet["$AH$7"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$7"].value, 18.88)
    assert_allclose(actual_test_sheet["$AJ$7"].value, 346.4)
    assert_allclose(actual_test_sheet["$AK$7"].value, 0.1211)
    assert_allclose(actual_test_sheet["$AL$7"].value, 0.06033)
    assert_allclose(actual_test_sheet["$AM$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$7"].value, 7399.0)
    assert actual_test_sheet["$B$8"].value == "Casing 1 heat loss"
    assert actual_test_sheet["$C$8"].value == "Yes"
    assert actual_test_sheet["$D$8"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 3.888)
    assert_allclose(actual_test_sheet["$H$8"].value, 1500.3234856434028)
    assert_allclose(actual_test_sheet["$I$8"].value, 5.16)
    assert_allclose(actual_test_sheet["$J$8"].value, 300.4)
    assert_allclose(actual_test_sheet["$K$8"].value, 15.07)
    assert_allclose(actual_test_sheet["$L$8"].value, 400.2)
    assert_allclose(actual_test_sheet["$M$8"].value, 0.06099)
    assert_allclose(actual_test_sheet["$N$8"].value, 300.6)
    assert_allclose(actual_test_sheet["$P$8"].value, 14.66)
    assert_allclose(actual_test_sheet["$Q$8"].value, 304.6)
    assert_allclose(actual_test_sheet["$S$8"].value, 25.99)
    assert_allclose(actual_test_sheet["$T$8"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$8"].value, 9071.0)
    assert_allclose(actual_test_sheet["$AD$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$AE$8"].value, 2.587)
    assert_allclose(actual_test_sheet["$AF$8"].value, 404.1501023257591)
    assert_allclose(actual_test_sheet["$AG$8"].value, 12.46)
    assert_allclose(actual_test_sheet["$AH$8"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$8"].value, 18.6)
    assert_allclose(actual_test_sheet["$AJ$8"].value, 344.1)
    assert_allclose(actual_test_sheet["$AK$8"].value, 0.1171)
    assert_allclose(actual_test_sheet["$AL$8"].value, 0.05892)
    assert_allclose(actual_test_sheet["$AM$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$8"].value, 7449.0)
    assert_allclose(actual_test_sheet["$D$9"].value, 5.5)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 4.325)
    assert_allclose(actual_test_sheet["$H$9"].value, 1656.259613599762)
    assert_allclose(actual_test_sheet["$I$9"].value, 5.182)
    assert_allclose(actual_test_sheet["$J$9"].value, 299.5)
    assert_allclose(actual_test_sheet["$K$9"].value, 14.95)
    assert_allclose(actual_test_sheet["$L$9"].value, 397.6)
    assert_allclose(actual_test_sheet["$M$9"].value, 0.0616)
    assert_allclose(actual_test_sheet["$N$9"].value, 299.7)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1625)
    assert_allclose(actual_test_sheet["$P$9"].value, 14.59)
    assert_allclose(actual_test_sheet["$Q$9"].value, 304.3)
    assert_allclose(actual_test_sheet["$S$9"].value, 26.15)
    assert_allclose(actual_test_sheet["$T$9"].value, 362.5)
    assert_allclose(actual_test_sheet["$U$9"].value, 4.8059)
    assert_allclose(actual_test_sheet["$V$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$9"].value, 9096.0)
    assert actual_test_sheet["$Z$9"].value == "Calculado"
    assert_allclose(actual_test_sheet["$AD$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$AE$9"].value, 3.3600000000000003)
    assert_allclose(actual_test_sheet["$AF$9"].value, 517.6023230905009)
    assert_allclose(actual_test_sheet["$AG$9"].value, 12.62)
    assert_allclose(actual_test_sheet["$AH$9"].value, 304.4)
    assert_allclose(actual_test_sheet["$AI$9"].value, 18.15)
    assert_allclose(actual_test_sheet["$AJ$9"].value, 339.9)
    assert_allclose(actual_test_sheet["$AK$9"].value, 0.1222)
    assert_allclose(actual_test_sheet["$AL$9"].value, 0.07412)
    assert_allclose(actual_test_sheet["$AM$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$9"].value, 7412.0)

    assert actual_test_sheet["$D$10"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 5.724)
    assert_allclose(actual_test_sheet["$H$10"].value, 2021.0086305580305)
    assert_allclose(actual_test_sheet["$I$10"].value, 5.592)
    assert_allclose(actual_test_sheet["$J$10"].value, 298.7)
    assert_allclose(actual_test_sheet["$K$10"].value, 14.78)
    assert_allclose(actual_test_sheet["$L$10"].value, 389.8)
    assert_allclose(actual_test_sheet["$M$10"].value, 0.05942)
    assert_allclose(actual_test_sheet["$N$10"].value, 299.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 14.27)
    assert_allclose(actual_test_sheet["$Q$10"].value, 304.1)
    assert_allclose(actual_test_sheet["$S$10"].value, 25.43)
    assert_allclose(actual_test_sheet["$T$10"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$10"].value, 9057.0)
    assert_allclose(actual_test_sheet["$AD$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$AE$10"].value, 4.105)
    assert_allclose(actual_test_sheet["$AF$10"].value, 628.8975623074246)
    assert_allclose(actual_test_sheet["$AG$10"].value, 12.69)
    assert_allclose(actual_test_sheet["$AH$10"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$10"].value, 16.78)
    assert_allclose(actual_test_sheet["$AJ$10"].value, 333.3)
    assert_allclose(actual_test_sheet["$AK$10"].value, 0.1079)
    assert_allclose(actual_test_sheet["$AL$10"].value, 0.06692)
    assert_allclose(actual_test_sheet["$AM$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$10"].value, 7330.0)
    assert_allclose(actual_test_sheet["$D$11"].value, 23.895)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 8.716)
    assert_allclose(actual_test_sheet["$H$11"].value, 2412.192118154552)
    assert_allclose(actual_test_sheet["$I$11"].value, 7.083)
    assert_allclose(actual_test_sheet["$J$11"].value, 298.9)
    assert_allclose(actual_test_sheet["$K$11"].value, 14.16)
    assert_allclose(actual_test_sheet["$L$11"].value, 377.1)
    assert_allclose(actual_test_sheet["$M$11"].value, 0.06504)
    assert_allclose(actual_test_sheet["$N$11"].value, 299.5)
    assert_allclose(actual_test_sheet["$P$11"].value, 13.1)
    assert_allclose(actual_test_sheet["$Q$11"].value, 303.5)
    assert_allclose(actual_test_sheet["$S$11"].value, 23.13)
    assert_allclose(actual_test_sheet["$T$11"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$11"].value, 9024.0)
    assert_allclose(actual_test_sheet["$AD$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$AE$11"].value, 4.9270000000000005)
    assert_allclose(actual_test_sheet["$AF$11"].value, 730.7765001154256)
    assert_allclose(actual_test_sheet["$AG$11"].value, 13.11)
    assert_allclose(actual_test_sheet["$AH$11"].value, 305.1)
    assert_allclose(actual_test_sheet["$AI$11"].value, 16.31)
    assert_allclose(actual_test_sheet["$AJ$11"].value, 335.1)
    assert_allclose(actual_test_sheet["$AK$11"].value, 0.1066)
    assert_allclose(actual_test_sheet["$AL$11"].value, 0.06367)
    assert_allclose(actual_test_sheet["$AM$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$11"].value, 7739.0)
    assert actual_test_sheet["$D$12"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$AD$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$AD$13"].value, 7.0)
    assert actual_test_sheet["$D$14"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$AD$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$15"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$AD$15"].value, 9.0)
    assert actual_test_sheet["$B$16"].value == "Casing 2 heat loss"
    assert actual_test_sheet["$C$16"].value == "Yes"
    assert actual_test_sheet["$D$16"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$AD$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$17"].value, 5.5)
    assert actual_test_sheet["$D$18"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$D$19"].value, 17.97)
    assert actual_test_sheet["$F$19"].value == "SECTION 1 - Tested points - Results"
    assert actual_test_sheet["$D$20"].value == "Ambient Temperature [ °C ]"
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
    assert actual_test_sheet["$AC$20"].value == "Mdiv (kg/h)"
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
    assert actual_test_sheet["$AC$21"].value == "Mdiv_sp"
    assert actual_test_sheet["$D$22"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 2.2254125053126814)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.013123464366914)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.6537022458531642)
    assert_allclose(actual_test_sheet["$J$22"].value, -0.002874637138687741)
    assert_allclose(actual_test_sheet["$K$22"].value, 1065720.5685238568)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.11859356895525477)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.019768609167195028)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.758705139247969)
    assert_allclose(actual_test_sheet["$O$22"].value, 140.6812831878591)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.032371638569451)
    assert_allclose(actual_test_sheet["$Q$22"].value, 70.59695674947551)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5809779675549773)
    assert_allclose(actual_test_sheet["$S$22"].value, 125.9627526579225)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.036611029658496)
    assert_allclose(actual_test_sheet["$U$22"].value, 1765.0690179703577)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.7743282337286901)
    assert_allclose(actual_test_sheet["$W$22"].value, 296.3768657453652)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.06192967919956646)
    assert_allclose(actual_test_sheet["$Y$22"].value, 4052.9975386877545)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.8468975361363551)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.7805812598976413)
    assert_allclose(actual_test_sheet["$AC$22"].value, 8215.58881702776)
    assert_allclose(actual_test_sheet["$D$23"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 2.196532014999917)
    assert_allclose(actual_test_sheet["$H$23"].value, 0.9999755637739081)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.6507428270979058)
    assert_allclose(actual_test_sheet["$J$23"].value, -0.005834055893946144)
    assert_allclose(actual_test_sheet["$K$23"].value, 1089590.9262789434)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.12124986648954703)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.022975244557738462)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.8817735215465565)
    assert_allclose(actual_test_sheet["$O$23"].value, 138.58577186440237)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.0169939962163526)
    assert_allclose(actual_test_sheet["$Q$23"].value, 68.68900157856706)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.565276442044267)
    assert_allclose(actual_test_sheet["$S$23"].value, 123.7302033961571)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0182382556426182)
    assert_allclose(actual_test_sheet["$U$23"].value, 2044.403213210027)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.8968709512189534)
    assert_allclose(actual_test_sheet["$W$23"].value, 337.7716614513198)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.07057936382374988)
    assert_allclose(actual_test_sheet["$Y$23"].value, 4497.604639878563)
    assert_allclose(actual_test_sheet["$Z$23"].value, 0.9398007898277291)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.7906608772031583)
    assert_allclose(actual_test_sheet["$AC$23"].value, 8018.074041006352)

    assert actual_test_sheet["$B$24"].value == "Curve Shape"
    assert actual_test_sheet["$C$24"].value == "No"
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 2.177620827286962)
    assert_allclose(actual_test_sheet["$H$24"].value, 0.9913662079959106)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.6535559724840474)
    assert_allclose(actual_test_sheet["$J$24"].value, -0.0030209105078045084)
    assert_allclose(actual_test_sheet["$K$24"].value, 1104133.840408922)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.12286820448603784)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.025293467001523705)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9707452477385319)
    assert_allclose(actual_test_sheet["$O$24"].value, 135.6992669763552)
    assert_allclose(actual_test_sheet["$P$24"].value, 0.9958117485606164)
    assert_allclose(actual_test_sheet["$Q$24"].value, 67.54548985918196)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5558659072961302)
    assert_allclose(actual_test_sheet["$S$24"].value, 120.89215590152328)
    assert_allclose(actual_test_sheet["$T$24"].value, 0.9948825312435051)
    assert_allclose(actual_test_sheet["$U$24"].value, 2247.503799562048)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9859703103364011)
    assert_allclose(actual_test_sheet["$W$24"].value, 368.319680328752)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.07696255100168252)
    assert_allclose(actual_test_sheet["$Y$24"].value, 4776.432749245249)
    assert_allclose(actual_test_sheet["$Z$24"].value, 0.998063553763347)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.7931540431947893)
    assert_allclose(actual_test_sheet["$AC$24"].value, 7806.0343686647275)
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.028362859987217)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9234162218454397)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.6524130555549584)
    assert_allclose(actual_test_sheet["$J$25"].value, -0.004163827436893475)
    assert_allclose(actual_test_sheet["$K$25"].value, 1195120.8418341428)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.13299325372150472)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.030996610253312327)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.1896278235638378)
    assert_allclose(actual_test_sheet["$O$25"].value, 124.68007500421281)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9149488148837808)
    assert_allclose(actual_test_sheet["$Q$25"].value, 61.103221332331145)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.5028492299844557)
    assert_allclose(actual_test_sheet["$S$25"].value, 110.1628806159674)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.906585912865739)
    assert_allclose(actual_test_sheet["$U$25"].value, 2741.2159487321574)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.2025597198977822)
    assert_allclose(actual_test_sheet["$W$25"].value, 450.11711645252683)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.09405460360083726)
    assert_allclose(actual_test_sheet["$Y$25"].value, 5313.4273855761185)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.110271723170303)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.7770307462705689)
    assert_allclose(actual_test_sheet["$AC$25"].value, 6958.776998845581)
    assert actual_test_sheet["$B$26"].value == "Balance line and div. wall leakage"
    assert actual_test_sheet["$C$26"].value == "Yes"
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 1.578450967616677)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.7185929389843275)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.6527016569242936)
    assert_allclose(actual_test_sheet["$J$26"].value, -0.0038752260675583017)
    assert_allclose(actual_test_sheet["$K$26"].value, 1516369.3458798889)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1687418427433828)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.037131561204681994)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.4250828713353563)
    assert_allclose(actual_test_sheet["$O$26"].value, 94.58082916388668)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.6940693414829873)
    assert_allclose(actual_test_sheet["$Q$26"].value, 42.57668472606889)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.3503850151099371)
    assert_allclose(actual_test_sheet["$S$26"].value, 77.54937829771534)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.6381929514106632)
    assert_allclose(actual_test_sheet["$U$26"].value, 3269.4926013563972)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.4343124293850336)
    assert_allclose(actual_test_sheet["$W$26"].value, 591.2049446646265)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.12353573033508713)
    assert_allclose(actual_test_sheet["$Y$26"].value, 5387.114920738161)
    assert_allclose(actual_test_sheet["$Z$26"].value, 1.1256691645398085)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.6276983767159285)
    assert_allclose(actual_test_sheet["$AC$26"].value, 4788.937978302228)
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert actual_test_sheet["$B$28"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$28"].value == "Yes"
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert actual_test_sheet["$B$30"].value == "Variable Speed"
    assert actual_test_sheet["$C$30"].value == "Yes"
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 2.1669792262932317)
    assert_allclose(actual_test_sheet["$H$32"].value, 0.9865215980013856)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.6565768829918519)
    assert_allclose(actual_test_sheet["$K$32"].value, 8986326.812762942)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.02605572065425804)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$32"].value, 134.98549318646468)
    assert_allclose(actual_test_sheet["$P$32"].value, 0.9905738107174333)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 120.21385888103846)
    assert_allclose(actual_test_sheet["$T$32"].value, 0.9933462382877855)
    assert_allclose(actual_test_sheet["$U$32"].value, 2279.4842562705835)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 4853.175977795146)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.014099500134807)
    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8467523371822481)
    assert actual_test_sheet["$F$34"].value == "SECTION 2 - Tested points - Results"
    assert actual_test_sheet["$G$35"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$35"].value == "Mach"
    assert actual_test_sheet["$K$35"].value == "Reynolds"
    assert actual_test_sheet["$M$35"].value == "Flow Coef."
    assert actual_test_sheet["$O$35"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$35"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$35"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$35"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$35"].value == "Power (kW)"
    assert actual_test_sheet["$Y$35"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$35"].value == "Polytropic Eff."
    assert actual_test_sheet["$AC$35"].value == "Mdiv"
    assert actual_test_sheet["$F$36"].value == "ERRO!"
    assert actual_test_sheet["$G$36"].value == "vi/vd"
    assert actual_test_sheet["$H$36"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$36"].value == "Mt"
    assert actual_test_sheet["$J$36"].value == "Mt - Msp"
    assert actual_test_sheet["$K$36"].value == "Re_t"
    assert actual_test_sheet["$L$36"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$36"].value == "ft"
    assert actual_test_sheet["$N$36"].value == "ft/fsp"
    assert actual_test_sheet["$O$36"].value == "Pdconv"
    assert actual_test_sheet["$P$36"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$36"].value == "Ht"
    assert actual_test_sheet["$R$36"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$36"].value == "Hconv"
    assert actual_test_sheet["$T$36"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$36"].value == "Qconv"
    assert actual_test_sheet["$V$36"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$36"].value == "Wt"
    assert actual_test_sheet["$X$36"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$36"].value == "Wconv"
    assert actual_test_sheet["$Z$36"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$36"].value == "ht"
    assert actual_test_sheet["$AB$36"].value == "Reynolds corr."
    assert actual_test_sheet["$AC$36"].value == "kg/h"

    assert_allclose(actual_test_sheet["$F$37"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$37"].value, 1.3227207253089355)
    assert_allclose(actual_test_sheet["$H$37"].value, 1.027364212958199)
    assert_allclose(actual_test_sheet["$I$37"].value, 0.4719605160746876)
    assert_allclose(actual_test_sheet["$J$37"].value, -0.06198613821683385)
    assert_allclose(actual_test_sheet["$K$37"].value, 1192374.3898159557)
    assert_allclose(actual_test_sheet["$L$37"].value, 0.1043429785471704)
    assert_allclose(actual_test_sheet["$M$37"].value, 0.008985131877381945)
    assert_allclose(actual_test_sheet["$N$37"].value, 0.7598590105162515)
    assert_allclose(actual_test_sheet["$O$37"].value, 259.26825231172256)
    assert_allclose(actual_test_sheet["$P$37"].value, 1.0352509675440127)
    assert_allclose(actual_test_sheet["$Q$37"].value, 23.729875113017336)
    assert_allclose(actual_test_sheet["$R$37"].value, 0.3849440362238192)
    assert_allclose(actual_test_sheet["$S$37"].value, 64.26756139002478)
    assert_allclose(actual_test_sheet["$T$37"].value, 1.0425429700709672)
    assert_allclose(actual_test_sheet["$U$37"].value, 527.8871685039355)
    assert_allclose(actual_test_sheet["$V$37"].value, 0.7572596536687259)
    assert_allclose(actual_test_sheet["$W$37"].value, 73.7582737108613)
    assert_allclose(actual_test_sheet["$X$37"].value, 0.02582120557005472)
    assert_allclose(actual_test_sheet["$Y$37"].value, 2348.7784837784966)
    assert_allclose(actual_test_sheet["$Z$37"].value, 0.8222574772548561)
    assert_allclose(actual_test_sheet["$AA$37"].value, 0.6675792203669783)
    assert_allclose(actual_test_sheet["$F$38"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$38"].value, 1.3192737459068735)
    assert_allclose(actual_test_sheet["$H$38"].value, 1.0246869257480393)
    assert_allclose(actual_test_sheet["$I$38"].value, 0.47506645243163736)
    assert_allclose(actual_test_sheet["$J$38"].value, -0.058880201859884074)
    assert_allclose(actual_test_sheet["$K$38"].value, 1194368.5372530876)
    assert_allclose(actual_test_sheet["$L$38"].value, 0.10451748353908377)
    assert_allclose(actual_test_sheet["$M$38"].value, 0.011184170506366536)
    assert_allclose(actual_test_sheet["$N$38"].value, 0.9458283807503725)
    assert_allclose(actual_test_sheet["$O$38"].value, 253.8033340052049)
    assert_allclose(actual_test_sheet["$P$38"].value, 1.013429699749261)
    assert_allclose(actual_test_sheet["$Q$38"].value, 23.06263900998732)
    assert_allclose(actual_test_sheet["$R$38"].value, 0.3741201883362368)
    assert_allclose(actual_test_sheet["$S$38"].value, 61.59804203504148)
    assert_allclose(actual_test_sheet["$T$38"].value, 0.9992382518459157)
    assert_allclose(actual_test_sheet["$U$38"].value, 658.4134958801715)
    assert_allclose(actual_test_sheet["$V$38"].value, 0.9445010328136374)
    assert_allclose(actual_test_sheet["$W$38"].value, 86.18665062742811)
    assert_allclose(actual_test_sheet["$X$38"].value, 0.030172116445800142)
    assert_allclose(actual_test_sheet["$Y$38"].value, 2708.1542883384054)
    assert_allclose(actual_test_sheet["$Z$38"].value, 0.9480673160645564)
    assert_allclose(actual_test_sheet["$AA$38"].value, 0.6922539242968327)
    assert_allclose(actual_test_sheet["$F$39"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$39"].value, 1.2866731198277017)
    assert_allclose(actual_test_sheet["$H$39"].value, 0.9993658463146237)
    assert_allclose(actual_test_sheet["$I$39"].value, 0.4730184033476288)
    assert_allclose(actual_test_sheet["$J$39"].value, -0.06092825094389265)
    assert_allclose(actual_test_sheet["$K$39"].value, 1205399.4462691715)
    assert_allclose(actual_test_sheet["$L$39"].value, 0.10548278262018757)
    assert_allclose(actual_test_sheet["$M$39"].value, 0.014395271717545245)
    assert_allclose(actual_test_sheet["$N$39"].value, 1.2173863525522004)
    assert_allclose(actual_test_sheet["$O$39"].value, 241.7474450697423)
    assert_allclose(actual_test_sheet["$P$39"].value, 0.965290868350672)
    assert_allclose(actual_test_sheet["$Q$39"].value, 20.761393895089576)
    assert_allclose(actual_test_sheet["$R$39"].value, 0.336789583828203)
    assert_allclose(actual_test_sheet["$S$39"].value, 55.997334307487435)
    assert_allclose(actual_test_sheet["$T$39"].value, 0.9083840426228799)
    assert_allclose(actual_test_sheet["$U$39"].value, 848.4569644799774)
    assert_allclose(actual_test_sheet["$V$39"].value, 1.2171203723246706)
    assert_allclose(actual_test_sheet["$W$39"].value, 99.7389247725241)
    assert_allclose(actual_test_sheet["$X$39"].value, 0.03491647987835607)
    assert_allclose(actual_test_sheet["$Y$39"].value, 3139.969438163065)
    assert_allclose(actual_test_sheet["$Z$39"].value, 1.0992366315991826)
    assert_allclose(actual_test_sheet["$AA$39"].value, 0.6994088180376883)
    assert_allclose(actual_test_sheet["$F$40"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$40"].value, 1.2056421414082092)
    assert_allclose(actual_test_sheet["$H$40"].value, 0.9364286549814107)
    assert_allclose(actual_test_sheet["$I$40"].value, 0.46779210993261205)
    assert_allclose(actual_test_sheet["$J$40"].value, -0.06615454435890938)
    assert_allclose(actual_test_sheet["$K$40"].value, 1198177.4782408962)
    assert_allclose(actual_test_sheet["$L$40"].value, 0.10485079852066409)
    assert_allclose(actual_test_sheet["$M$40"].value, 0.017686218956384073)
    assert_allclose(actual_test_sheet["$N$40"].value, 1.4956967821253158)
    assert_allclose(actual_test_sheet["$O$40"].value, 215.36656657409637)
    assert_allclose(actual_test_sheet["$P$40"].value, 0.8599527494573406)
    assert_allclose(actual_test_sheet["$Q$40"].value, 15.807602800854134)
    assert_allclose(actual_test_sheet["$R$40"].value, 0.2564296017658226)
    assert_allclose(actual_test_sheet["$S$40"].value, 43.63211968695928)
    assert_allclose(actual_test_sheet["$T$40"].value, 0.7077965720976442)
    assert_allclose(actual_test_sheet["$U$40"].value, 1045.1073218776332)
    assert_allclose(actual_test_sheet["$V$40"].value, 1.499217362783475)
    assert_allclose(actual_test_sheet["$W$40"].value, 99.51984685850736)
    assert_allclose(actual_test_sheet["$X$40"].value, 0.03483978535218182)
    assert_allclose(actual_test_sheet["$Y$40"].value, 3229.577888085955)
    assert_allclose(actual_test_sheet["$Z$40"].value, 1.1306066473257326)
    assert_allclose(actual_test_sheet["$AA$40"].value, 0.6520328511936325)
    assert_allclose(actual_test_sheet["$F$41"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$41"].value, 1.1250598933659246)
    assert_allclose(actual_test_sheet["$H$41"].value, 0.8738399949155996)
    assert_allclose(actual_test_sheet["$I$41"].value, 0.493933640164255)
    assert_allclose(actual_test_sheet["$J$41"].value, -0.04001301412726643)
    assert_allclose(actual_test_sheet["$K$41"].value, 1303631.450002704)
    assert_allclose(actual_test_sheet["$L$41"].value, 0.11407892486020633)
    assert_allclose(actual_test_sheet["$M$41"].value, 0.019465196266921888)
    assert_allclose(actual_test_sheet["$N$41"].value, 1.646142202110626)
    assert_allclose(actual_test_sheet["$O$41"].value, 188.87645261951585)
    assert_allclose(actual_test_sheet["$P$41"].value, 0.7541784563948085)
    assert_allclose(actual_test_sheet["$Q$41"].value, 12.411074754890574)
    assert_allclose(actual_test_sheet["$R$41"].value, 0.20133140976381822)
    assert_allclose(actual_test_sheet["$S$41"].value, 30.836443930475674)
    assert_allclose(actual_test_sheet["$T$41"].value, 0.5002261972662125)
    assert_allclose(actual_test_sheet["$U$41"].value, 1151.531542498374)
    assert_allclose(actual_test_sheet["$V$41"].value, 1.6518840181932388)
    assert_allclose(actual_test_sheet["$W$41"].value, 128.82560797648563)
    assert_allclose(actual_test_sheet["$X$41"].value, 0.045099110091540565)
    assert_allclose(actual_test_sheet["$Y$41"].value, 3442.5685162823206)
    assert_allclose(actual_test_sheet["$Z$41"].value, 1.205170143981208)
    assert_allclose(actual_test_sheet["$AA$41"].value, 0.47466777978262975)
    assert_allclose(actual_test_sheet["$F$42"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$43"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$44"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$45"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$46"].value, 10.0)
    assert actual_test_sheet["$F$47"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$47"].value, 1.299193468118952)
    assert_allclose(actual_test_sheet["$H$47"].value, 1.0090904673340748)
    assert_allclose(actual_test_sheet["$I$47"].value, 0.5359031363608555)
    assert_allclose(actual_test_sheet["$J$47"].value, 0.0019564820693340756)
    assert_allclose(actual_test_sheet["$K$47"].value, 11395503.382886197)
    assert_allclose(actual_test_sheet["$L$47"].value, 0.9972042130141959)
    assert_allclose(actual_test_sheet["$M$47"].value, 0.01193842859636084)
    assert_allclose(actual_test_sheet["$N$47"].value, 1.0096148464092323)
    assert_allclose(actual_test_sheet["$O$47"].value, 250.92384311405652)
    assert_allclose(actual_test_sheet["$P$47"].value, 1.00193197218518)
    assert actual_test_sheet["$Q$47"].value == " - "
    assert actual_test_sheet["$R$47"].value == " - "
    assert_allclose(actual_test_sheet["$S$47"].value, 60.26725476164641)
    assert_allclose(actual_test_sheet["$T$47"].value, 1.0187627666086212)
    assert_allclose(actual_test_sheet["$U$47"].value, 703.804461215436)
    assert_allclose(actual_test_sheet["$V$47"].value, 1.0096148464092323)
    assert actual_test_sheet["$W$47"].value == " - "
    assert actual_test_sheet["$X$47"].value == " - "

    assert_allclose(actual_test_sheet["$Y$47"].value, 2738.0263243762206)
    assert_allclose(actual_test_sheet["$Z$47"].value, 0.958524881630044)
    assert_allclose(actual_test_sheet["$AB$47"].value, 0.6962100690828491)


def test_2sec_reynolds_casing_balance_divwall():
    wb = xl.Book(beta_2section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$4"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$8"].value = "Yes"  # set casing
    actual_test_sheet["$C$16"].value = "Yes"  # set casing
    actual_test_sheet["$C$26"].value = "Yes"  # set balance and divwall
    actual_test_sheet["$C$28"].value = "No"  # set buffer

    runpy.run_path(str(script_2sec), run_name="test_script")

    assert actual_test_sheet["$B$3"].value == "Opções"
    assert actual_test_sheet["$F$3"].value == "SECTION 1 - Tested points - Measurements"
    assert actual_test_sheet["$X$3"].value == "Ordenar por:"
    assert actual_test_sheet["$Y$3"].value == "Vazão Seção 1"
    assert (
        actual_test_sheet["$AD$3"].value == "SECTION 2 - Tested points - Measurements"
    )
    assert actual_test_sheet["$B$4"].value == "Reynolds correction"
    assert actual_test_sheet["$C$4"].value == "Yes"
    assert actual_test_sheet["$D$4"].value == "Rugosidade [in] - Case 1"
    assert actual_test_sheet["$G$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$H$4"].value, 3774.0)
    assert actual_test_sheet["$I$4"].value == "rpm"
    assert actual_test_sheet["$AE$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$AF$4"].value, 3774.0)
    assert actual_test_sheet["$AG$4"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$5"].value, 0.01)
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$M$5"].value == "Mbuf"
    assert actual_test_sheet["$N$5"].value == "Tbuf"
    assert actual_test_sheet["$O$5"].value == "Mbal"
    assert actual_test_sheet["$P$5"].value == "Pend"
    assert actual_test_sheet["$Q$5"].value == "Tend"
    assert actual_test_sheet["$R$5"].value == "Mdiv"
    assert actual_test_sheet["$S$5"].value == "Pdiv"
    assert actual_test_sheet["$T$5"].value == "Tdiv"
    assert actual_test_sheet["$U$5"].value == "Md1f"
    assert actual_test_sheet["$V$5"].value == "Gas Selection"
    assert actual_test_sheet["$W$5"].value == "Speed"
    assert actual_test_sheet["$AE$5"].value == "Ms"
    assert actual_test_sheet["$AF$5"].value == "Qs"
    assert actual_test_sheet["$AG$5"].value == "Ps"
    assert actual_test_sheet["$AH$5"].value == "Ts"
    assert actual_test_sheet["$AI$5"].value == "Pd"
    assert actual_test_sheet["$AJ$5"].value == "Td"
    assert actual_test_sheet["$AK$5"].value == "Mbal"
    assert actual_test_sheet["$AL$5"].value == "Mbuf"
    assert actual_test_sheet["$AM$5"].value == "Gas Selection"
    assert actual_test_sheet["$AN$5"].value == "Speed"
    assert actual_test_sheet["$D$6"].value == "Rugosidade [in] - Case 2"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$M$6"].value == "kg/s"
    assert actual_test_sheet["$N$6"].value == "kelvin"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "bar"
    assert actual_test_sheet["$Q$6"].value == "kelvin"
    assert actual_test_sheet["$R$6"].value == "kg/h"
    assert actual_test_sheet["$S$6"].value == "bar"
    assert actual_test_sheet["$T$6"].value == "kelvin"
    assert actual_test_sheet["$U$6"].value == "kg/s"
    assert actual_test_sheet["$W$6"].value == "rpm"
    assert actual_test_sheet["$AE$6"].value == "kg/s"
    assert actual_test_sheet["$AF$6"].value == "m³/h"
    assert actual_test_sheet["$AG$6"].value == "bar"
    assert actual_test_sheet["$AH$6"].value == "kelvin"
    assert actual_test_sheet["$AI$6"].value == "bar"
    assert actual_test_sheet["$AJ$6"].value == "kelvin"
    assert actual_test_sheet["$AK$6"].value == "kg/s"
    assert actual_test_sheet["$AL$6"].value == "kg/s"
    assert actual_test_sheet["$AN$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$7"].value, 0.01)
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 3.277)
    assert_allclose(actual_test_sheet["$H$7"].value, 1298.3249050526144)
    assert_allclose(actual_test_sheet["$I$7"].value, 5.038)
    assert_allclose(actual_test_sheet["$J$7"].value, 300.9)
    assert_allclose(actual_test_sheet["$K$7"].value, 15.04)
    assert_allclose(actual_test_sheet["$L$7"].value, 404.3)
    assert_allclose(actual_test_sheet["$M$7"].value, 0.06143)
    assert_allclose(actual_test_sheet["$N$7"].value, 301.0)
    assert_allclose(actual_test_sheet["$P$7"].value, 14.6)
    assert_allclose(actual_test_sheet["$Q$7"].value, 304.8)
    assert_allclose(actual_test_sheet["$S$7"].value, 26.27)
    assert_allclose(actual_test_sheet["$T$7"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$7"].value, 9123.0)
    assert actual_test_sheet["$Z$7"].value == "Status"
    assert_allclose(actual_test_sheet["$AD$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AE$7"].value, 2.075)
    assert_allclose(actual_test_sheet["$AF$7"].value, 322.5064631506056)
    assert_allclose(actual_test_sheet["$AG$7"].value, 12.52)
    assert_allclose(actual_test_sheet["$AH$7"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$7"].value, 18.88)
    assert_allclose(actual_test_sheet["$AJ$7"].value, 346.4)
    assert_allclose(actual_test_sheet["$AK$7"].value, 0.1211)
    assert_allclose(actual_test_sheet["$AL$7"].value, 0.06033)
    assert_allclose(actual_test_sheet["$AM$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$7"].value, 7399.0)
    assert actual_test_sheet["$B$8"].value == "Casing 1 heat loss"
    assert actual_test_sheet["$C$8"].value == "Yes"
    assert actual_test_sheet["$D$8"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 3.888)
    assert_allclose(actual_test_sheet["$H$8"].value, 1500.3234856434028)
    assert_allclose(actual_test_sheet["$I$8"].value, 5.16)
    assert_allclose(actual_test_sheet["$J$8"].value, 300.4)
    assert_allclose(actual_test_sheet["$K$8"].value, 15.07)
    assert_allclose(actual_test_sheet["$L$8"].value, 400.2)
    assert_allclose(actual_test_sheet["$M$8"].value, 0.06099)
    assert_allclose(actual_test_sheet["$N$8"].value, 300.6)
    assert_allclose(actual_test_sheet["$P$8"].value, 14.66)
    assert_allclose(actual_test_sheet["$Q$8"].value, 304.6)
    assert_allclose(actual_test_sheet["$S$8"].value, 25.99)
    assert_allclose(actual_test_sheet["$T$8"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$8"].value, 9071.0)
    assert_allclose(actual_test_sheet["$AD$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$AE$8"].value, 2.587)
    assert_allclose(actual_test_sheet["$AF$8"].value, 404.1501023257591)
    assert_allclose(actual_test_sheet["$AG$8"].value, 12.46)
    assert_allclose(actual_test_sheet["$AH$8"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$8"].value, 18.6)
    assert_allclose(actual_test_sheet["$AJ$8"].value, 344.1)
    assert_allclose(actual_test_sheet["$AK$8"].value, 0.1171)
    assert_allclose(actual_test_sheet["$AL$8"].value, 0.05892)
    assert_allclose(actual_test_sheet["$AM$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$8"].value, 7449.0)
    assert_allclose(actual_test_sheet["$D$9"].value, 5.5)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 4.325)
    assert_allclose(actual_test_sheet["$H$9"].value, 1656.259613599762)
    assert_allclose(actual_test_sheet["$I$9"].value, 5.182)
    assert_allclose(actual_test_sheet["$J$9"].value, 299.5)
    assert_allclose(actual_test_sheet["$K$9"].value, 14.95)
    assert_allclose(actual_test_sheet["$L$9"].value, 397.6)
    assert_allclose(actual_test_sheet["$M$9"].value, 0.0616)
    assert_allclose(actual_test_sheet["$N$9"].value, 299.7)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1625)
    assert_allclose(actual_test_sheet["$P$9"].value, 14.59)
    assert_allclose(actual_test_sheet["$Q$9"].value, 304.3)
    assert_allclose(actual_test_sheet["$S$9"].value, 26.15)
    assert_allclose(actual_test_sheet["$T$9"].value, 362.5)
    assert_allclose(actual_test_sheet["$U$9"].value, 4.8059)
    assert_allclose(actual_test_sheet["$V$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$9"].value, 9096.0)
    assert actual_test_sheet["$Z$9"].value == "Calculado"
    assert_allclose(actual_test_sheet["$AD$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$AE$9"].value, 3.3600000000000003)
    assert_allclose(actual_test_sheet["$AF$9"].value, 517.6023230905009)
    assert_allclose(actual_test_sheet["$AG$9"].value, 12.62)
    assert_allclose(actual_test_sheet["$AH$9"].value, 304.4)
    assert_allclose(actual_test_sheet["$AI$9"].value, 18.15)
    assert_allclose(actual_test_sheet["$AJ$9"].value, 339.9)
    assert_allclose(actual_test_sheet["$AK$9"].value, 0.1222)
    assert_allclose(actual_test_sheet["$AL$9"].value, 0.07412)

    assert_allclose(actual_test_sheet["$AM$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$9"].value, 7412.0)
    assert actual_test_sheet["$D$10"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 5.724)
    assert_allclose(actual_test_sheet["$H$10"].value, 2021.0086305580305)
    assert_allclose(actual_test_sheet["$I$10"].value, 5.592)
    assert_allclose(actual_test_sheet["$J$10"].value, 298.7)
    assert_allclose(actual_test_sheet["$K$10"].value, 14.78)
    assert_allclose(actual_test_sheet["$L$10"].value, 389.8)
    assert_allclose(actual_test_sheet["$M$10"].value, 0.05942)
    assert_allclose(actual_test_sheet["$N$10"].value, 299.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 14.27)
    assert_allclose(actual_test_sheet["$Q$10"].value, 304.1)
    assert_allclose(actual_test_sheet["$S$10"].value, 25.43)
    assert_allclose(actual_test_sheet["$T$10"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$10"].value, 9057.0)
    assert_allclose(actual_test_sheet["$AD$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$AE$10"].value, 4.105)
    assert_allclose(actual_test_sheet["$AF$10"].value, 628.8975623074246)
    assert_allclose(actual_test_sheet["$AG$10"].value, 12.69)
    assert_allclose(actual_test_sheet["$AH$10"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$10"].value, 16.78)
    assert_allclose(actual_test_sheet["$AJ$10"].value, 333.3)
    assert_allclose(actual_test_sheet["$AK$10"].value, 0.1079)
    assert_allclose(actual_test_sheet["$AL$10"].value, 0.06692)
    assert_allclose(actual_test_sheet["$AM$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$10"].value, 7330.0)
    assert_allclose(actual_test_sheet["$D$11"].value, 23.895)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 8.716)
    assert_allclose(actual_test_sheet["$H$11"].value, 2412.192118154552)
    assert_allclose(actual_test_sheet["$I$11"].value, 7.083)
    assert_allclose(actual_test_sheet["$J$11"].value, 298.9)
    assert_allclose(actual_test_sheet["$K$11"].value, 14.16)
    assert_allclose(actual_test_sheet["$L$11"].value, 377.1)
    assert_allclose(actual_test_sheet["$M$11"].value, 0.06504)
    assert_allclose(actual_test_sheet["$N$11"].value, 299.5)
    assert_allclose(actual_test_sheet["$P$11"].value, 13.1)
    assert_allclose(actual_test_sheet["$Q$11"].value, 303.5)
    assert_allclose(actual_test_sheet["$S$11"].value, 23.13)
    assert_allclose(actual_test_sheet["$T$11"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$11"].value, 9024.0)
    assert_allclose(actual_test_sheet["$AD$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$AE$11"].value, 4.9270000000000005)
    assert_allclose(actual_test_sheet["$AF$11"].value, 730.7765001154256)
    assert_allclose(actual_test_sheet["$AG$11"].value, 13.11)
    assert_allclose(actual_test_sheet["$AH$11"].value, 305.1)
    assert_allclose(actual_test_sheet["$AI$11"].value, 16.31)
    assert_allclose(actual_test_sheet["$AJ$11"].value, 335.1)
    assert_allclose(actual_test_sheet["$AK$11"].value, 0.1066)
    assert_allclose(actual_test_sheet["$AL$11"].value, 0.06367)
    assert_allclose(actual_test_sheet["$AM$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$11"].value, 7739.0)
    assert actual_test_sheet["$D$12"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$AD$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$AD$13"].value, 7.0)
    assert actual_test_sheet["$D$14"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$AD$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$15"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$AD$15"].value, 9.0)
    assert actual_test_sheet["$B$16"].value == "Casing 2 heat loss"
    assert actual_test_sheet["$C$16"].value == "Yes"
    assert actual_test_sheet["$D$16"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$AD$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$17"].value, 5.5)
    assert actual_test_sheet["$D$18"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$D$19"].value, 17.97)
    assert actual_test_sheet["$F$19"].value == "SECTION 1 - Tested points - Results"
    assert actual_test_sheet["$D$20"].value == "Ambient Temperature [ °C ]"
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
    assert actual_test_sheet["$AC$20"].value == "Mdiv (kg/h)"
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
    assert actual_test_sheet["$AC$21"].value == "Mdiv_sp"
    assert actual_test_sheet["$D$22"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 2.2254125053126814)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.013123464366914)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.6537022458531642)
    assert_allclose(actual_test_sheet["$J$22"].value, -0.002874637138687741)
    assert_allclose(actual_test_sheet["$K$22"].value, 1065720.5685238568)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.11859356895525477)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.019768609167195028)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.758705139247969)
    assert_allclose(actual_test_sheet["$O$22"].value, 140.92372200958684)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.0341507449151452)
    assert_allclose(actual_test_sheet["$Q$22"].value, 70.59695674947551)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5809779675549773)
    assert_allclose(actual_test_sheet["$S$22"].value, 126.05977237318726)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.0374094538340213)
    assert_allclose(actual_test_sheet["$U$22"].value, 1735.3277501394302)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.7612808666547071)
    assert_allclose(actual_test_sheet["$W$22"].value, 296.3768657453652)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.06192967919956646)
    assert_allclose(actual_test_sheet["$Y$22"].value, 4047.3046712740606)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.8457079782004849)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.7805812598976413)
    assert_allclose(actual_test_sheet["$AC$22"].value, 9058.404860771017)
    assert_allclose(actual_test_sheet["$D$23"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 2.196532014999917)
    assert_allclose(actual_test_sheet["$H$23"].value, 0.9999755637739081)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.6507428270979058)
    assert_allclose(actual_test_sheet["$J$23"].value, -0.005834055893946144)
    assert_allclose(actual_test_sheet["$K$23"].value, 1089590.9262789434)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.12124986648954703)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.022975244557738462)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.8817735215465565)
    assert_allclose(actual_test_sheet["$O$23"].value, 138.78319913089777)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.0184427910097436)
    assert_allclose(actual_test_sheet["$Q$23"].value, 68.68900157856706)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.565276442044267)
    assert_allclose(actual_test_sheet["$S$23"].value, 123.79328377080877)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0187573758645816)
    assert_allclose(actual_test_sheet["$U$23"].value, 2015.4149742377137)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.8841539346865646)

    assert_allclose(actual_test_sheet["$W$23"].value, 337.7716614513198)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.07057936382374988)
    assert_allclose(actual_test_sheet["$Y$23"].value, 4492.160311321824)
    assert_allclose(actual_test_sheet["$Z$23"].value, 0.9386631655393829)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.7906608772031583)
    assert_allclose(actual_test_sheet["$AC$23"].value, 8838.234404346198)
    assert actual_test_sheet["$B$24"].value == "Curve Shape"
    assert actual_test_sheet["$C$24"].value == "No"
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 2.177620827286962)
    assert_allclose(actual_test_sheet["$H$24"].value, 0.9913662079959106)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.6535559724840474)
    assert_allclose(actual_test_sheet["$J$24"].value, -0.0030209105078045084)
    assert_allclose(actual_test_sheet["$K$24"].value, 1104133.840408922)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.12286820448603784)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.025293467001523705)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9707452477385319)
    assert_allclose(actual_test_sheet["$O$24"].value, 135.86694756966608)
    assert_allclose(actual_test_sheet["$P$24"].value, 0.997042251190035)
    assert_allclose(actual_test_sheet["$Q$24"].value, 67.54548985918196)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5558659072961302)
    assert_allclose(actual_test_sheet["$S$24"].value, 120.93670007907347)
    assert_allclose(actual_test_sheet["$T$24"].value, 0.995249107749506)
    assert_allclose(actual_test_sheet["$U$24"].value, 2218.5926985912965)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9732871339155856)
    assert_allclose(actual_test_sheet["$W$24"].value, 368.319680328752)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.07696255100168252)
    assert_allclose(actual_test_sheet["$Y$24"].value, 4769.428342992523)
    assert_allclose(actual_test_sheet["$Z$24"].value, 0.9965999421176678)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.7931540431947893)
    assert_allclose(actual_test_sheet["$AC$24"].value, 8603.29495440357)
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.028362859987217)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9234162218454397)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.6524130555549584)
    assert_allclose(actual_test_sheet["$J$25"].value, -0.004163827436893475)
    assert_allclose(actual_test_sheet["$K$25"].value, 1195120.8418341428)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.13299325372150472)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.030996610253312327)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.1896278235638378)
    assert_allclose(actual_test_sheet["$O$25"].value, 124.77804864216208)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9156677819194399)
    assert_allclose(actual_test_sheet["$Q$25"].value, 61.103221332331145)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.5028492299844557)
    assert_allclose(actual_test_sheet["$S$25"].value, 110.17252764951958)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9066653031709893)
    assert_allclose(actual_test_sheet["$U$25"].value, 2715.0319981408184)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.1910729326917244)
    assert_allclose(actual_test_sheet["$W$25"].value, 450.11711645252683)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.09405460360083726)
    assert_allclose(actual_test_sheet["$Y$25"].value, 5304.990379091295)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.1085087613288118)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.7770307462705689)
    assert_allclose(actual_test_sheet["$AC$25"].value, 7660.971572939568)
    assert actual_test_sheet["$B$26"].value == "Balance line and div. wall leakage"
    assert actual_test_sheet["$C$26"].value == "Yes"
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 1.578450967616677)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.7185929389843275)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.6527016569242936)
    assert_allclose(actual_test_sheet["$J$26"].value, -0.0038752260675583017)
    assert_allclose(actual_test_sheet["$K$26"].value, 1516369.3458798889)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1687418427433828)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.037131561204681994)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.4250828713353563)
    assert_allclose(actual_test_sheet["$O$26"].value, 94.60379519004809)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.6942378747343368)
    assert_allclose(actual_test_sheet["$Q$26"].value, 42.57668472606889)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.3503850151099371)
    assert_allclose(actual_test_sheet["$S$26"].value, 77.54638826143233)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.6381683448938585)
    assert_allclose(actual_test_sheet["$U$26"].value, 3245.9651291751197)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.4239910279028536)
    assert_allclose(actual_test_sheet["$W$26"].value, 591.2049446646265)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.12353573033508713)
    assert_allclose(actual_test_sheet["$Y$26"].value, 5371.495995918927)
    assert_allclose(actual_test_sheet["$Z$26"].value, 1.1224054988651457)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.6276983767159285)
    assert_allclose(actual_test_sheet["$AC$26"].value, 5260.43892579696)
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert actual_test_sheet["$B$28"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$28"].value == "No"
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert actual_test_sheet["$B$30"].value == "Variable Speed"
    assert actual_test_sheet["$C$30"].value == "Yes"
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 2.1650896938303235)
    assert_allclose(actual_test_sheet["$H$32"].value, 0.9856613845936308)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.6565768829918519)
    assert_allclose(actual_test_sheet["$K$32"].value, 8986326.812762942)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.02605572065425804)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$32"].value, 134.506820905124)
    assert_allclose(actual_test_sheet["$P$32"].value, 0.9870611352838038)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 119.64656711317632)
    assert_allclose(actual_test_sheet["$T$32"].value, 0.9886586161711447)
    assert_allclose(actual_test_sheet["$U$32"].value, 2279.4842562705835)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 4892.099990808326)
    assert_allclose(actual_test_sheet["$Z$32"].value, 1.0222329002671138)
    assert_allclose(actual_test_sheet["$AB$32"].value, 0.8526289829938674)
    assert actual_test_sheet["$F$34"].value == "SECTION 2 - Tested points - Results"
    assert actual_test_sheet["$G$35"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$35"].value == "Mach"
    assert actual_test_sheet["$K$35"].value == "Reynolds"
    assert actual_test_sheet["$M$35"].value == "Flow Coef."
    assert actual_test_sheet["$O$35"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$35"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$35"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$35"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$35"].value == "Power (kW)"
    assert actual_test_sheet["$Y$35"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$35"].value == "Polytropic Eff."
    assert actual_test_sheet["$AC$35"].value == "Mdiv"
    assert actual_test_sheet["$F$36"].value == "ERRO!"
    assert actual_test_sheet["$G$36"].value == "vi/vd"
    assert actual_test_sheet["$H$36"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$36"].value == "Mt"
    assert actual_test_sheet["$J$36"].value == "Mt - Msp"
    assert actual_test_sheet["$K$36"].value == "Re_t"
    assert actual_test_sheet["$L$36"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$36"].value == "ft"
    assert actual_test_sheet["$N$36"].value == "ft/fsp"
    assert actual_test_sheet["$O$36"].value == "Pdconv"
    assert actual_test_sheet["$P$36"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$36"].value == "Ht"
    assert actual_test_sheet["$R$36"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$36"].value == "Hconv"
    assert actual_test_sheet["$T$36"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$36"].value == "Qconv"
    assert actual_test_sheet["$V$36"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$36"].value == "Wt"
    assert actual_test_sheet["$X$36"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$36"].value == "Wconv"
    assert actual_test_sheet["$Z$36"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$36"].value == "ht"
    assert actual_test_sheet["$AB$36"].value == "Reynolds corr."
    assert actual_test_sheet["$AC$36"].value == "kg/h"

    assert_allclose(actual_test_sheet["$F$37"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$37"].value, 1.3227207253089355)
    assert_allclose(actual_test_sheet["$H$37"].value, 1.027364212958199)
    assert_allclose(actual_test_sheet["$I$37"].value, 0.4719605160746876)
    assert_allclose(actual_test_sheet["$J$37"].value, -0.06198613821683385)
    assert_allclose(actual_test_sheet["$K$37"].value, 1192374.3898159557)
    assert_allclose(actual_test_sheet["$L$37"].value, 0.1043429785471704)
    assert_allclose(actual_test_sheet["$M$37"].value, 0.008985131877381945)
    assert_allclose(actual_test_sheet["$N$37"].value, 0.7598590105162515)
    assert_allclose(actual_test_sheet["$O$37"].value, 258.41564214170575)
    assert_allclose(actual_test_sheet["$P$37"].value, 1.0318465186939216)
    assert_allclose(actual_test_sheet["$Q$37"].value, 23.729875113017336)
    assert_allclose(actual_test_sheet["$R$37"].value, 0.3849440362238192)
    assert_allclose(actual_test_sheet["$S$37"].value, 64.26786760061998)
    assert_allclose(actual_test_sheet["$T$37"].value, 1.042547937393462)
    assert_allclose(actual_test_sheet["$U$37"].value, 525.455743710925)
    assert_allclose(actual_test_sheet["$V$37"].value, 0.7537717494222658)
    assert_allclose(actual_test_sheet["$W$37"].value, 73.7582737108613)
    assert_allclose(actual_test_sheet["$X$37"].value, 0.02582120557005472)
    assert_allclose(actual_test_sheet["$Y$37"].value, 2329.8836987749605)
    assert_allclose(actual_test_sheet["$Z$37"].value, 0.8156428142044322)
    assert_allclose(actual_test_sheet["$AA$37"].value, 0.6675792203669783)
    assert_allclose(actual_test_sheet["$F$38"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$38"].value, 1.3192737459068735)
    assert_allclose(actual_test_sheet["$H$38"].value, 1.0246869257480393)
    assert_allclose(actual_test_sheet["$I$38"].value, 0.47506645243163736)
    assert_allclose(actual_test_sheet["$J$38"].value, -0.058880201859884074)
    assert_allclose(actual_test_sheet["$K$38"].value, 1194368.5372530876)
    assert_allclose(actual_test_sheet["$L$38"].value, 0.10451748353908377)
    assert_allclose(actual_test_sheet["$M$38"].value, 0.011184170506366536)
    assert_allclose(actual_test_sheet["$N$38"].value, 0.9458283807503725)
    assert_allclose(actual_test_sheet["$O$38"].value, 252.96729489538)
    assert_allclose(actual_test_sheet["$P$38"].value, 1.010091418684635)
    assert_allclose(actual_test_sheet["$Q$38"].value, 23.06263900998732)
    assert_allclose(actual_test_sheet["$R$38"].value, 0.3741201883362368)
    assert_allclose(actual_test_sheet["$S$38"].value, 61.59825039452966)
    assert_allclose(actual_test_sheet["$T$38"].value, 0.9992416318359908)
    assert_allclose(actual_test_sheet["$U$38"].value, 656.1645324935737)
    assert_allclose(actual_test_sheet["$V$38"].value, 0.9412748713593341)
    assert_allclose(actual_test_sheet["$W$38"].value, 86.18665062742811)
    assert_allclose(actual_test_sheet["$X$38"].value, 0.030172116445800142)
    assert_allclose(actual_test_sheet["$Y$38"].value, 2689.320987990569)
    assert_allclose(actual_test_sheet["$Z$38"].value, 0.9414741774866336)
    assert_allclose(actual_test_sheet["$AA$38"].value, 0.6922539242968327)
    assert_allclose(actual_test_sheet["$F$39"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$39"].value, 1.2866731198277017)
    assert_allclose(actual_test_sheet["$H$39"].value, 0.9993658463146237)
    assert_allclose(actual_test_sheet["$I$39"].value, 0.4730184033476288)
    assert_allclose(actual_test_sheet["$J$39"].value, -0.06092825094389265)
    assert_allclose(actual_test_sheet["$K$39"].value, 1205399.4462691715)
    assert_allclose(actual_test_sheet["$L$39"].value, 0.10548278262018757)
    assert_allclose(actual_test_sheet["$M$39"].value, 0.014395271717545245)
    assert_allclose(actual_test_sheet["$N$39"].value, 1.2173863525522004)
    assert_allclose(actual_test_sheet["$O$39"].value, 240.94534363147415)
    assert_allclose(actual_test_sheet["$P$39"].value, 0.962088099470828)
    assert_allclose(actual_test_sheet["$Q$39"].value, 20.761393895089576)
    assert_allclose(actual_test_sheet["$R$39"].value, 0.336789583828203)
    assert_allclose(actual_test_sheet["$S$39"].value, 55.99749821673381)
    assert_allclose(actual_test_sheet["$T$39"].value, 0.9083867015448748)
    assert_allclose(actual_test_sheet["$U$39"].value, 844.4486334890973)
    assert_allclose(actual_test_sheet["$V$39"].value, 1.2113703796765336)
    assert_allclose(actual_test_sheet["$W$39"].value, 99.7389247725241)
    assert_allclose(actual_test_sheet["$X$39"].value, 0.03491647987835607)
    assert_allclose(actual_test_sheet["$Y$39"].value, 3113.937706749353)
    assert_allclose(actual_test_sheet["$Z$39"].value, 1.0901234751441808)
    assert_allclose(actual_test_sheet["$AA$39"].value, 0.6994088180376883)
    assert_allclose(actual_test_sheet["$F$40"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$40"].value, 1.2056421414082092)
    assert_allclose(actual_test_sheet["$H$40"].value, 0.9364286549814107)
    assert_allclose(actual_test_sheet["$I$40"].value, 0.46779210993261205)
    assert_allclose(actual_test_sheet["$J$40"].value, -0.06615454435890938)
    assert_allclose(actual_test_sheet["$K$40"].value, 1198177.4782408962)
    assert_allclose(actual_test_sheet["$L$40"].value, 0.10485079852066409)
    assert_allclose(actual_test_sheet["$M$40"].value, 0.017686218956384073)
    assert_allclose(actual_test_sheet["$N$40"].value, 1.4956967821253158)
    assert_allclose(actual_test_sheet["$O$40"].value, 214.64067092494892)
    assert_allclose(actual_test_sheet["$P$40"].value, 0.8570542681877852)
    assert_allclose(actual_test_sheet["$Q$40"].value, 15.807602800854134)
    assert_allclose(actual_test_sheet["$R$40"].value, 0.2564296017658226)
    assert_allclose(actual_test_sheet["$S$40"].value, 43.632245013601604)
    assert_allclose(actual_test_sheet["$T$40"].value, 0.7077986051358846)
    assert_allclose(actual_test_sheet["$U$40"].value, 1041.9175308319827)
    assert_allclose(actual_test_sheet["$V$40"].value, 1.4946415742312538)
    assert_allclose(actual_test_sheet["$W$40"].value, 99.51984685850736)
    assert_allclose(actual_test_sheet["$X$40"].value, 0.03483978535218182)
    assert_allclose(actual_test_sheet["$Y$40"].value, 3208.052796704473)
    assert_allclose(actual_test_sheet["$Z$40"].value, 1.1230711698597842)
    assert_allclose(actual_test_sheet["$AA$40"].value, 0.6520328511936325)
    assert_allclose(actual_test_sheet["$F$41"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$41"].value, 1.1250598933659246)
    assert_allclose(actual_test_sheet["$H$41"].value, 0.8738399949155996)
    assert_allclose(actual_test_sheet["$I$41"].value, 0.493933640164255)
    assert_allclose(actual_test_sheet["$J$41"].value, -0.04001301412726643)
    assert_allclose(actual_test_sheet["$K$41"].value, 1303631.450002704)
    assert_allclose(actual_test_sheet["$L$41"].value, 0.11407892486020633)
    assert_allclose(actual_test_sheet["$M$41"].value, 0.019465196266921888)
    assert_allclose(actual_test_sheet["$N$41"].value, 1.646142202110626)
    assert_allclose(actual_test_sheet["$O$41"].value, 188.231587093148)
    assert_allclose(actual_test_sheet["$P$41"].value, 0.7516035261665389)
    assert_allclose(actual_test_sheet["$Q$41"].value, 12.411074754890574)
    assert_allclose(actual_test_sheet["$R$41"].value, 0.20133140976381822)
    assert_allclose(actual_test_sheet["$S$41"].value, 30.83657276103302)
    assert_allclose(actual_test_sheet["$T$41"].value, 0.5002282871446673)
    assert_allclose(actual_test_sheet["$U$41"].value, 1149.3716779034742)
    assert_allclose(actual_test_sheet["$V$41"].value, 1.6487856698857009)
    assert_allclose(actual_test_sheet["$W$41"].value, 128.82560797648563)
    assert_allclose(actual_test_sheet["$X$41"].value, 0.045099110091540565)
    assert_allclose(actual_test_sheet["$Y$41"].value, 3423.512298450862)
    assert_allclose(actual_test_sheet["$Z$41"].value, 1.198498966725315)
    assert_allclose(actual_test_sheet["$AA$41"].value, 0.47466777978262975)
    assert_allclose(actual_test_sheet["$F$42"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$43"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$44"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$45"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$46"].value, 10.0)
    assert actual_test_sheet["$F$47"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$47"].value, 1.2998337055489053)
    assert_allclose(actual_test_sheet["$H$47"].value, 1.0095877431465308)
    assert_allclose(actual_test_sheet["$I$47"].value, 0.5366545402064236)
    assert_allclose(actual_test_sheet["$J$47"].value, 0.0027078859149021195)
    assert_allclose(actual_test_sheet["$K$47"].value, 11382792.909517206)
    assert_allclose(actual_test_sheet["$L$47"].value, 0.9960919376572338)
    assert_allclose(actual_test_sheet["$M$47"].value, 0.011983160912262317)
    assert_allclose(actual_test_sheet["$N$47"].value, 1.013397790695733)
    assert_allclose(actual_test_sheet["$O$47"].value, 249.75710370532687)
    assert_allclose(actual_test_sheet["$P$47"].value, 0.9972732139647295)
    assert actual_test_sheet["$Q$47"].value == " - "
    assert actual_test_sheet["$R$47"].value == " - "
    assert_allclose(actual_test_sheet["$S$47"].value, 60.110175727692145)
    assert_allclose(actual_test_sheet["$T$47"].value, 1.0161074893466926)
    assert_allclose(actual_test_sheet["$U$47"].value, 706.441558990729)
    assert_allclose(actual_test_sheet["$V$47"].value, 1.0133977906957328)
    assert actual_test_sheet["$W$47"].value == " - "
    assert actual_test_sheet["$X$47"].value == " - "
    assert_allclose(actual_test_sheet["$Y$47"].value, 2711.973078506034)
    assert_allclose(actual_test_sheet["$Z$47"].value, 0.9494041934206316)
    assert_allclose(actual_test_sheet["$AB$47"].value, 0.6963098557196155)


def test_2sec_reynolds_casing():
    wb = xl.Book(beta_2section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$4"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$8"].value = "Yes"  # set casing
    actual_test_sheet["$C$16"].value = "Yes"  # set casing
    actual_test_sheet["$C$26"].value = "No"  # set balance and divwall
    actual_test_sheet["$C$28"].value = "No"  # set buffer

    runpy.run_path(str(script_2sec), run_name="test_script")

    assert actual_test_sheet["$B$3"].value == "Opções"
    assert actual_test_sheet["$F$3"].value == "SECTION 1 - Tested points - Measurements"
    assert actual_test_sheet["$X$3"].value == "Ordenar por:"
    assert actual_test_sheet["$Y$3"].value == "Vazão Seção 1"
    assert (
        actual_test_sheet["$AD$3"].value == "SECTION 2 - Tested points - Measurements"
    )
    assert actual_test_sheet["$B$4"].value == "Reynolds correction"
    assert actual_test_sheet["$C$4"].value == "Yes"
    assert actual_test_sheet["$D$4"].value == "Rugosidade [in] - Case 1"
    assert actual_test_sheet["$G$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$H$4"].value, 3774.0)
    assert actual_test_sheet["$I$4"].value == "rpm"
    assert actual_test_sheet["$AE$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$AF$4"].value, 3774.0)
    assert actual_test_sheet["$AG$4"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$5"].value, 0.01)
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$M$5"].value == "Mbuf"
    assert actual_test_sheet["$N$5"].value == "Tbuf"
    assert actual_test_sheet["$O$5"].value == "Mbal"
    assert actual_test_sheet["$P$5"].value == "Pend"
    assert actual_test_sheet["$Q$5"].value == "Tend"
    assert actual_test_sheet["$R$5"].value == "Mdiv"
    assert actual_test_sheet["$S$5"].value == "Pdiv"
    assert actual_test_sheet["$T$5"].value == "Tdiv"
    assert actual_test_sheet["$U$5"].value == "Md1f"
    assert actual_test_sheet["$V$5"].value == "Gas Selection"
    assert actual_test_sheet["$W$5"].value == "Speed"
    assert actual_test_sheet["$AE$5"].value == "Ms"
    assert actual_test_sheet["$AF$5"].value == "Qs"
    assert actual_test_sheet["$AG$5"].value == "Ps"
    assert actual_test_sheet["$AH$5"].value == "Ts"
    assert actual_test_sheet["$AI$5"].value == "Pd"
    assert actual_test_sheet["$AJ$5"].value == "Td"
    assert actual_test_sheet["$AK$5"].value == "Mbal"
    assert actual_test_sheet["$AL$5"].value == "Mbuf"
    assert actual_test_sheet["$AM$5"].value == "Gas Selection"
    assert actual_test_sheet["$AN$5"].value == "Speed"
    assert actual_test_sheet["$D$6"].value == "Rugosidade [in] - Case 2"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$M$6"].value == "kg/s"
    assert actual_test_sheet["$N$6"].value == "kelvin"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "bar"
    assert actual_test_sheet["$Q$6"].value == "kelvin"
    assert actual_test_sheet["$R$6"].value == "kg/h"
    assert actual_test_sheet["$S$6"].value == "bar"
    assert actual_test_sheet["$T$6"].value == "kelvin"
    assert actual_test_sheet["$U$6"].value == "kg/s"
    assert actual_test_sheet["$W$6"].value == "rpm"
    assert actual_test_sheet["$AE$6"].value == "kg/s"
    assert actual_test_sheet["$AF$6"].value == "m³/h"
    assert actual_test_sheet["$AG$6"].value == "bar"
    assert actual_test_sheet["$AH$6"].value == "kelvin"
    assert actual_test_sheet["$AI$6"].value == "bar"
    assert actual_test_sheet["$AJ$6"].value == "kelvin"
    assert actual_test_sheet["$AK$6"].value == "kg/s"
    assert actual_test_sheet["$AL$6"].value == "kg/s"
    assert actual_test_sheet["$AN$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$7"].value, 0.01)
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 3.277)
    assert_allclose(actual_test_sheet["$H$7"].value, 1298.3249050526144)
    assert_allclose(actual_test_sheet["$I$7"].value, 5.038)
    assert_allclose(actual_test_sheet["$J$7"].value, 300.9)
    assert_allclose(actual_test_sheet["$K$7"].value, 15.04)
    assert_allclose(actual_test_sheet["$L$7"].value, 404.3)
    assert_allclose(actual_test_sheet["$M$7"].value, 0.06143)
    assert_allclose(actual_test_sheet["$N$7"].value, 301.0)
    assert_allclose(actual_test_sheet["$P$7"].value, 14.6)
    assert_allclose(actual_test_sheet["$Q$7"].value, 304.8)
    assert_allclose(actual_test_sheet["$S$7"].value, 26.27)
    assert_allclose(actual_test_sheet["$T$7"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$7"].value, 9123.0)
    assert actual_test_sheet["$Z$7"].value == "Status"
    assert_allclose(actual_test_sheet["$AD$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AE$7"].value, 2.075)
    assert_allclose(actual_test_sheet["$AF$7"].value, 322.5064631506056)
    assert_allclose(actual_test_sheet["$AG$7"].value, 12.52)
    assert_allclose(actual_test_sheet["$AH$7"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$7"].value, 18.88)
    assert_allclose(actual_test_sheet["$AJ$7"].value, 346.4)
    assert_allclose(actual_test_sheet["$AK$7"].value, 0.1211)
    assert_allclose(actual_test_sheet["$AL$7"].value, 0.06033)
    assert_allclose(actual_test_sheet["$AM$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$7"].value, 7399.0)
    assert actual_test_sheet["$B$8"].value == "Casing 1 heat loss"
    assert actual_test_sheet["$C$8"].value == "Yes"
    assert actual_test_sheet["$D$8"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 3.888)
    assert_allclose(actual_test_sheet["$H$8"].value, 1500.3234856434028)
    assert_allclose(actual_test_sheet["$I$8"].value, 5.16)
    assert_allclose(actual_test_sheet["$J$8"].value, 300.4)
    assert_allclose(actual_test_sheet["$K$8"].value, 15.07)
    assert_allclose(actual_test_sheet["$L$8"].value, 400.2)
    assert_allclose(actual_test_sheet["$M$8"].value, 0.06099)
    assert_allclose(actual_test_sheet["$N$8"].value, 300.6)
    assert_allclose(actual_test_sheet["$P$8"].value, 14.66)
    assert_allclose(actual_test_sheet["$Q$8"].value, 304.6)
    assert_allclose(actual_test_sheet["$S$8"].value, 25.99)
    assert_allclose(actual_test_sheet["$T$8"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$8"].value, 9071.0)
    assert_allclose(actual_test_sheet["$AD$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$AE$8"].value, 2.587)
    assert_allclose(actual_test_sheet["$AF$8"].value, 404.1501023257591)
    assert_allclose(actual_test_sheet["$AG$8"].value, 12.46)
    assert_allclose(actual_test_sheet["$AH$8"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$8"].value, 18.6)
    assert_allclose(actual_test_sheet["$AJ$8"].value, 344.1)
    assert_allclose(actual_test_sheet["$AK$8"].value, 0.1171)
    assert_allclose(actual_test_sheet["$AL$8"].value, 0.05892)
    assert_allclose(actual_test_sheet["$AM$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$8"].value, 7449.0)
    assert_allclose(actual_test_sheet["$D$9"].value, 5.5)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 4.325)
    assert_allclose(actual_test_sheet["$H$9"].value, 1656.259613599762)
    assert_allclose(actual_test_sheet["$I$9"].value, 5.182)
    assert_allclose(actual_test_sheet["$J$9"].value, 299.5)
    assert_allclose(actual_test_sheet["$K$9"].value, 14.95)
    assert_allclose(actual_test_sheet["$L$9"].value, 397.6)
    assert_allclose(actual_test_sheet["$M$9"].value, 0.0616)
    assert_allclose(actual_test_sheet["$N$9"].value, 299.7)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1625)
    assert_allclose(actual_test_sheet["$P$9"].value, 14.59)
    assert_allclose(actual_test_sheet["$Q$9"].value, 304.3)
    assert_allclose(actual_test_sheet["$S$9"].value, 26.15)
    assert_allclose(actual_test_sheet["$T$9"].value, 362.5)
    assert_allclose(actual_test_sheet["$U$9"].value, 4.8059)
    assert_allclose(actual_test_sheet["$V$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$9"].value, 9096.0)
    assert actual_test_sheet["$Z$9"].value == "Calculado"
    assert_allclose(actual_test_sheet["$AD$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$AE$9"].value, 3.3600000000000003)
    assert_allclose(actual_test_sheet["$AF$9"].value, 517.6023230905009)
    assert_allclose(actual_test_sheet["$AG$9"].value, 12.62)
    assert_allclose(actual_test_sheet["$AH$9"].value, 304.4)
    assert_allclose(actual_test_sheet["$AI$9"].value, 18.15)
    assert_allclose(actual_test_sheet["$AJ$9"].value, 339.9)
    assert_allclose(actual_test_sheet["$AK$9"].value, 0.1222)
    assert_allclose(actual_test_sheet["$AL$9"].value, 0.07412)

    assert_allclose(actual_test_sheet["$AM$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$9"].value, 7412.0)
    assert actual_test_sheet["$D$10"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 5.724)
    assert_allclose(actual_test_sheet["$H$10"].value, 2021.0086305580305)
    assert_allclose(actual_test_sheet["$I$10"].value, 5.592)
    assert_allclose(actual_test_sheet["$J$10"].value, 298.7)
    assert_allclose(actual_test_sheet["$K$10"].value, 14.78)
    assert_allclose(actual_test_sheet["$L$10"].value, 389.8)
    assert_allclose(actual_test_sheet["$M$10"].value, 0.05942)
    assert_allclose(actual_test_sheet["$N$10"].value, 299.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 14.27)
    assert_allclose(actual_test_sheet["$Q$10"].value, 304.1)
    assert_allclose(actual_test_sheet["$S$10"].value, 25.43)
    assert_allclose(actual_test_sheet["$T$10"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$10"].value, 9057.0)
    assert_allclose(actual_test_sheet["$AD$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$AE$10"].value, 4.105)
    assert_allclose(actual_test_sheet["$AF$10"].value, 628.8975623074246)
    assert_allclose(actual_test_sheet["$AG$10"].value, 12.69)
    assert_allclose(actual_test_sheet["$AH$10"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$10"].value, 16.78)
    assert_allclose(actual_test_sheet["$AJ$10"].value, 333.3)
    assert_allclose(actual_test_sheet["$AK$10"].value, 0.1079)
    assert_allclose(actual_test_sheet["$AL$10"].value, 0.06692)
    assert_allclose(actual_test_sheet["$AM$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$10"].value, 7330.0)
    assert_allclose(actual_test_sheet["$D$11"].value, 23.895)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 8.716)
    assert_allclose(actual_test_sheet["$H$11"].value, 2412.192118154552)
    assert_allclose(actual_test_sheet["$I$11"].value, 7.083)
    assert_allclose(actual_test_sheet["$J$11"].value, 298.9)
    assert_allclose(actual_test_sheet["$K$11"].value, 14.16)
    assert_allclose(actual_test_sheet["$L$11"].value, 377.1)
    assert_allclose(actual_test_sheet["$M$11"].value, 0.06504)
    assert_allclose(actual_test_sheet["$N$11"].value, 299.5)
    assert_allclose(actual_test_sheet["$P$11"].value, 13.1)
    assert_allclose(actual_test_sheet["$Q$11"].value, 303.5)
    assert_allclose(actual_test_sheet["$S$11"].value, 23.13)
    assert_allclose(actual_test_sheet["$T$11"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$11"].value, 9024.0)
    assert_allclose(actual_test_sheet["$AD$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$AE$11"].value, 4.9270000000000005)
    assert_allclose(actual_test_sheet["$AF$11"].value, 730.7765001154256)
    assert_allclose(actual_test_sheet["$AG$11"].value, 13.11)
    assert_allclose(actual_test_sheet["$AH$11"].value, 305.1)
    assert_allclose(actual_test_sheet["$AI$11"].value, 16.31)
    assert_allclose(actual_test_sheet["$AJ$11"].value, 335.1)
    assert_allclose(actual_test_sheet["$AK$11"].value, 0.1066)
    assert_allclose(actual_test_sheet["$AL$11"].value, 0.06367)
    assert_allclose(actual_test_sheet["$AM$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$11"].value, 7739.0)
    assert actual_test_sheet["$D$12"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$AD$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$AD$13"].value, 7.0)
    assert actual_test_sheet["$D$14"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$AD$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$15"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$AD$15"].value, 9.0)
    assert actual_test_sheet["$B$16"].value == "Casing 2 heat loss"
    assert actual_test_sheet["$C$16"].value == "Yes"
    assert actual_test_sheet["$D$16"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$AD$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$17"].value, 5.5)
    assert actual_test_sheet["$D$18"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$D$19"].value, 17.97)
    assert actual_test_sheet["$F$19"].value == "SECTION 1 - Tested points - Results"
    assert actual_test_sheet["$D$20"].value == "Ambient Temperature [ °C ]"
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
    assert actual_test_sheet["$AC$20"].value == "Mdiv (kg/h)"
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
    assert actual_test_sheet["$AC$21"].value == "Mdiv_sp"
    assert actual_test_sheet["$D$22"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 2.2254125053126814)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.013123464366914)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.6537022458531642)
    assert_allclose(actual_test_sheet["$J$22"].value, -0.002874637138687741)
    assert_allclose(actual_test_sheet["$K$22"].value, 1065720.5685238568)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.11859356895525477)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.019768609167195028)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.758705139247969)
    assert_allclose(actual_test_sheet["$O$22"].value, 139.51382979739554)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.0238044308901117)
    assert_allclose(actual_test_sheet["$Q$22"].value, 70.59695674947551)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5809779675549773)
    assert_allclose(actual_test_sheet["$S$22"].value, 125.82076510007934)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.0354425424237483)
    assert_allclose(actual_test_sheet["$U$22"].value, 1729.456420067326)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.758705139247969)
    assert_allclose(actual_test_sheet["$W$22"].value, 296.3768657453652)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.06192967919956646)
    assert_allclose(actual_test_sheet["$Y$22"].value, 3632.41228438798)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.7590137878237206)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.7805812598976413)
    assert_allclose(actual_test_sheet["$D$23"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 2.196532014999917)
    assert_allclose(actual_test_sheet["$H$23"].value, 0.9999755637739081)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.6507428270979058)
    assert_allclose(actual_test_sheet["$J$23"].value, -0.005834055893946144)
    assert_allclose(actual_test_sheet["$K$23"].value, 1089590.9262789434)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.12124986648954703)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.022975244557738462)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.8817735215465565)
    assert_allclose(actual_test_sheet["$O$23"].value, 137.63077374753976)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.0099858644422084)
    assert_allclose(actual_test_sheet["$Q$23"].value, 68.68900157856706)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.565276442044267)
    assert_allclose(actual_test_sheet["$S$23"].value, 123.7842829951949)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0186833039418908)
    assert_allclose(actual_test_sheet["$U$23"].value, 2009.9888599616459)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.8817735215465565)
    assert_allclose(actual_test_sheet["$W$23"].value, 337.7716614513198)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.07057936382374988)
    assert_allclose(actual_test_sheet["$Y$23"].value, 4101.788596925143)
    assert_allclose(actual_test_sheet["$Z$23"].value, 0.8570927130670838)

    assert_allclose(actual_test_sheet["$AA$23"].value, 0.7906608772031583)
    assert actual_test_sheet["$B$24"].value == "Curve Shape"
    assert actual_test_sheet["$C$24"].value == "No"
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 2.177620827286962)
    assert_allclose(actual_test_sheet["$H$24"].value, 0.9913662079959106)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.6535559724840474)
    assert_allclose(actual_test_sheet["$J$24"].value, -0.0030209105078045084)
    assert_allclose(actual_test_sheet["$K$24"].value, 1104133.840408922)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.12286820448603784)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.025293467001523705)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9707452477385319)
    assert_allclose(actual_test_sheet["$O$24"].value, 134.88673101778494)
    assert_allclose(actual_test_sheet["$P$24"].value, 0.9898490571496655)
    assert_allclose(actual_test_sheet["$Q$24"].value, 67.54548985918196)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5558659072961302)
    assert_allclose(actual_test_sheet["$S$24"].value, 121.0411888921828)
    assert_allclose(actual_test_sheet["$T$24"].value, 0.9961089988987508)
    assert_allclose(actual_test_sheet["$U$24"].value, 2212.7985090694706)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9707452477385319)
    assert_allclose(actual_test_sheet["$W$24"].value, 368.319680328752)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.07696255100168252)
    assert_allclose(actual_test_sheet["$Y$24"].value, 4402.230547059357)
    assert_allclose(actual_test_sheet["$Z$24"].value, 0.9198718154208073)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.7931540431947893)
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.028362859987217)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9234162218454397)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.6524130555549584)
    assert_allclose(actual_test_sheet["$J$25"].value, -0.004163827436893475)
    assert_allclose(actual_test_sheet["$K$25"].value, 1195120.8418341428)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.13299325372150472)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.030996610253312327)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.1896278235638378)
    assert_allclose(actual_test_sheet["$O$25"].value, 124.20456715635945)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.911459361241355)
    assert_allclose(actual_test_sheet["$Q$25"].value, 61.103221332331145)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.5028492299844557)
    assert_allclose(actual_test_sheet["$S$25"].value, 110.44554447887691)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9089120963747134)
    assert_allclose(actual_test_sheet["$U$25"].value, 2711.7378946352073)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.1896278235638376)
    assert_allclose(actual_test_sheet["$W$25"].value, 450.11711645252683)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.09405460360083726)
    assert_allclose(actual_test_sheet["$Y$25"].value, 5024.558194516815)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.0499108164984883)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.7770307462705689)
    assert actual_test_sheet["$B$26"].value == "Balance line and div. wall leakage"
    assert actual_test_sheet["$C$26"].value == "No"
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 1.578450967616677)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.7185929389843275)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.6527016569242936)
    assert_allclose(actual_test_sheet["$J$26"].value, -0.0038752260675583017)
    assert_allclose(actual_test_sheet["$K$26"].value, 1516369.3458798889)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1687418427433828)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.037131561204681994)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.4250828713353563)
    assert_allclose(actual_test_sheet["$O$26"].value, 94.46701253622521)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.6932341126896985)
    assert_allclose(actual_test_sheet["$Q$26"].value, 42.57668472606889)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.3503850151099371)
    assert_allclose(actual_test_sheet["$S$26"].value, 77.69546535455225)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.6393951754904971)
    assert_allclose(actual_test_sheet["$U$26"].value, 3248.4539690898223)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.4250828713353563)
    assert_allclose(actual_test_sheet["$W$26"].value, 591.2049446646265)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.12353573033508713)
    assert_allclose(actual_test_sheet["$Y$26"].value, 5229.887935602968)
    assert_allclose(actual_test_sheet["$Z$26"].value, 1.0928156665906699)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.6276983767159285)
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert actual_test_sheet["$B$28"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$28"].value == "No"
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert actual_test_sheet["$B$30"].value == "Variable Speed"
    assert actual_test_sheet["$C$30"].value == "Yes"
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 2.1178674208970003)
    assert_allclose(actual_test_sheet["$H$32"].value, 0.9641633510222025)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.6565768829918519)
    assert_allclose(actual_test_sheet["$K$32"].value, 8986326.812762942)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.02605572065425804)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$32"].value, 133.45900632931168)
    assert_allclose(actual_test_sheet["$P$32"].value, 0.97937188177377)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 119.65524266369356)
    assert_allclose(actual_test_sheet["$T$32"].value, 0.9887303036250839)
    assert_allclose(actual_test_sheet["$U$32"].value, 2279.4842562705835)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 4492.108800827213)
    assert_allclose(actual_test_sheet["$Z$32"].value, 0.9386524021203194)
    assert_allclose(actual_test_sheet["$AB$32"].value, 0.7946634638078004)
    assert actual_test_sheet["$F$34"].value == "SECTION 2 - Tested points - Results"
    assert actual_test_sheet["$G$35"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$35"].value == "Mach"
    assert actual_test_sheet["$K$35"].value == "Reynolds"
    assert actual_test_sheet["$M$35"].value == "Flow Coef."
    assert actual_test_sheet["$O$35"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$35"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$35"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$35"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$35"].value == "Power (kW)"
    assert actual_test_sheet["$Y$35"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$35"].value == "Polytropic Eff."
    assert actual_test_sheet["$AC$35"].value == "Mdiv"
    assert actual_test_sheet["$F$36"].value == "ERRO!"
    assert actual_test_sheet["$G$36"].value == "vi/vd"
    assert actual_test_sheet["$H$36"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$36"].value == "Mt"
    assert actual_test_sheet["$J$36"].value == "Mt - Msp"
    assert actual_test_sheet["$K$36"].value == "Re_t"
    assert actual_test_sheet["$L$36"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$36"].value == "ft"
    assert actual_test_sheet["$N$36"].value == "ft/fsp"
    assert actual_test_sheet["$O$36"].value == "Pdconv"
    assert actual_test_sheet["$P$36"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$36"].value == "Ht"
    assert actual_test_sheet["$R$36"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$36"].value == "Hconv"
    assert actual_test_sheet["$T$36"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$36"].value == "Qconv"
    assert actual_test_sheet["$V$36"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$36"].value == "Wt"
    assert actual_test_sheet["$X$36"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$36"].value == "Wconv"

    assert actual_test_sheet["$Z$36"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$36"].value == "ht"
    assert actual_test_sheet["$AB$36"].value == "Reynolds corr."
    assert actual_test_sheet["$AC$36"].value == "kg/h"
    assert_allclose(actual_test_sheet["$F$37"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$37"].value, 1.3227207253089355)
    assert_allclose(actual_test_sheet["$H$37"].value, 1.027364212958199)
    assert_allclose(actual_test_sheet["$I$37"].value, 0.4719605160746876)
    assert_allclose(actual_test_sheet["$J$37"].value, -0.06198613821683385)
    assert_allclose(actual_test_sheet["$K$37"].value, 1192374.3898159557)
    assert_allclose(actual_test_sheet["$L$37"].value, 0.1043429785471704)
    assert_allclose(actual_test_sheet["$M$37"].value, 0.008985131877381945)
    assert_allclose(actual_test_sheet["$N$37"].value, 0.7598590105162515)
    assert_allclose(actual_test_sheet["$O$37"].value, 256.205775927783)
    assert_allclose(actual_test_sheet["$P$37"].value, 1.0230225839633564)
    assert_allclose(actual_test_sheet["$Q$37"].value, 23.729875113017336)
    assert_allclose(actual_test_sheet["$R$37"].value, 0.3849440362238192)
    assert_allclose(actual_test_sheet["$S$37"].value, 64.26725897782735)
    assert_allclose(actual_test_sheet["$T$37"].value, 1.0425380643657611)
    assert_allclose(actual_test_sheet["$U$37"].value, 529.6991851874122)
    assert_allclose(actual_test_sheet["$V$37"].value, 0.7598590105162514)
    assert_allclose(actual_test_sheet["$W$37"].value, 73.7582737108613)
    assert_allclose(actual_test_sheet["$X$37"].value, 0.02582120557005472)
    assert_allclose(actual_test_sheet["$Y$37"].value, 2323.0592436796796)
    assert_allclose(actual_test_sheet["$Z$37"].value, 0.8132537173742971)
    assert_allclose(actual_test_sheet["$AA$37"].value, 0.6675792203669783)
    assert_allclose(actual_test_sheet["$F$38"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$38"].value, 1.3192737459068735)
    assert_allclose(actual_test_sheet["$H$38"].value, 1.0246869257480393)
    assert_allclose(actual_test_sheet["$I$38"].value, 0.47506645243163736)
    assert_allclose(actual_test_sheet["$J$38"].value, -0.058880201859884074)
    assert_allclose(actual_test_sheet["$K$38"].value, 1194368.5372530876)
    assert_allclose(actual_test_sheet["$L$38"].value, 0.10451748353908377)
    assert_allclose(actual_test_sheet["$M$38"].value, 0.011184170506366536)
    assert_allclose(actual_test_sheet["$N$38"].value, 0.9458283807503725)
    assert_allclose(actual_test_sheet["$O$38"].value, 250.7935454282655)
    assert_allclose(actual_test_sheet["$P$38"].value, 1.00141169712612)
    assert_allclose(actual_test_sheet["$Q$38"].value, 23.06263900998732)
    assert_allclose(actual_test_sheet["$R$38"].value, 0.3741201883362368)
    assert_allclose(actual_test_sheet["$S$38"].value, 61.59794594302738)
    assert_allclose(actual_test_sheet["$T$38"].value, 0.9992366930493533)
    assert_allclose(actual_test_sheet["$U$38"].value, 659.3387926928933)
    assert_allclose(actual_test_sheet["$V$38"].value, 0.9458283807503722)
    assert_allclose(actual_test_sheet["$W$38"].value, 86.18665062742811)
    assert_allclose(actual_test_sheet["$X$38"].value, 0.030172116445800142)
    assert_allclose(actual_test_sheet["$Y$38"].value, 2673.872209609843)
    assert_allclose(actual_test_sheet["$Z$38"].value, 0.9360658881882875)
    assert_allclose(actual_test_sheet["$AA$38"].value, 0.6922539242968327)
    assert_allclose(actual_test_sheet["$F$39"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$39"].value, 1.2866731198277017)
    assert_allclose(actual_test_sheet["$H$39"].value, 0.9993658463146237)
    assert_allclose(actual_test_sheet["$I$39"].value, 0.4730184033476288)
    assert_allclose(actual_test_sheet["$J$39"].value, -0.06092825094389265)
    assert_allclose(actual_test_sheet["$K$39"].value, 1205399.4462691715)
    assert_allclose(actual_test_sheet["$L$39"].value, 0.10548278262018757)
    assert_allclose(actual_test_sheet["$M$39"].value, 0.014395271717545245)
    assert_allclose(actual_test_sheet["$N$39"].value, 1.2173863525522004)
    assert_allclose(actual_test_sheet["$O$39"].value, 238.85667085916256)
    assert_allclose(actual_test_sheet["$P$39"].value, 0.9537480868038755)
    assert_allclose(actual_test_sheet["$Q$39"].value, 20.761393895089576)
    assert_allclose(actual_test_sheet["$R$39"].value, 0.336789583828203)
    assert_allclose(actual_test_sheet["$S$39"].value, 55.997369881426245)
    assert_allclose(actual_test_sheet["$T$39"].value, 0.9083846197003203)
    assert_allclose(actual_test_sheet["$U$39"].value, 848.6423798107802)
    assert_allclose(actual_test_sheet["$V$39"].value, 1.2173863525522002)
    assert_allclose(actual_test_sheet["$W$39"].value, 99.7389247725241)
    assert_allclose(actual_test_sheet["$X$39"].value, 0.03491647987835607)
    assert_allclose(actual_test_sheet["$Y$39"].value, 3097.160358483433)
    assert_allclose(actual_test_sheet["$Z$39"].value, 1.0842500817375924)
    assert_allclose(actual_test_sheet["$AA$39"].value, 0.6994088180376883)
    assert_allclose(actual_test_sheet["$F$40"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$40"].value, 1.2056421414082092)
    assert_allclose(actual_test_sheet["$H$40"].value, 0.9364286549814107)
    assert_allclose(actual_test_sheet["$I$40"].value, 0.46779210993261205)
    assert_allclose(actual_test_sheet["$J$40"].value, -0.06615454435890938)
    assert_allclose(actual_test_sheet["$K$40"].value, 1198177.4782408962)
    assert_allclose(actual_test_sheet["$L$40"].value, 0.10485079852066409)
    assert_allclose(actual_test_sheet["$M$40"].value, 0.017686218956384073)
    assert_allclose(actual_test_sheet["$N$40"].value, 1.4956967821253158)
    assert_allclose(actual_test_sheet["$O$40"].value, 212.74867949012344)
    assert_allclose(actual_test_sheet["$P$40"].value, 0.8494995986668401)
    assert_allclose(actual_test_sheet["$Q$40"].value, 15.807602800854134)
    assert_allclose(actual_test_sheet["$R$40"].value, 0.2564296017658226)
    assert_allclose(actual_test_sheet["$S$40"].value, 43.6322356455406)
    assert_allclose(actual_test_sheet["$T$40"].value, 0.7077984531679876)
    assert_allclose(actual_test_sheet["$U$40"].value, 1042.653118294857)
    assert_allclose(actual_test_sheet["$V$40"].value, 1.4956967821253153)
    assert_allclose(actual_test_sheet["$W$40"].value, 99.51984685850736)
    assert_allclose(actual_test_sheet["$X$40"].value, 0.03483978535218182)
    assert_allclose(actual_test_sheet["$Y$40"].value, 3177.69951305158)
    assert_allclose(actual_test_sheet["$Z$40"].value, 1.1124451297222406)
    assert_allclose(actual_test_sheet["$AA$40"].value, 0.6520328511936325)
    assert_allclose(actual_test_sheet["$F$41"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$41"].value, 1.1250598933659246)
    assert_allclose(actual_test_sheet["$H$41"].value, 0.8738399949155996)
    assert_allclose(actual_test_sheet["$I$41"].value, 0.493933640164255)
    assert_allclose(actual_test_sheet["$J$41"].value, -0.04001301412726643)
    assert_allclose(actual_test_sheet["$K$41"].value, 1303631.450002704)
    assert_allclose(actual_test_sheet["$L$41"].value, 0.11407892486020633)
    assert_allclose(actual_test_sheet["$M$41"].value, 0.019465196266921888)
    assert_allclose(actual_test_sheet["$N$41"].value, 1.646142202110626)
    assert_allclose(actual_test_sheet["$O$41"].value, 186.55052798222547)
    assert_allclose(actual_test_sheet["$P$41"].value, 0.7448911035865895)
    assert_allclose(actual_test_sheet["$Q$41"].value, 12.411074754890574)
    assert_allclose(actual_test_sheet["$R$41"].value, 0.20133140976381822)
    assert_allclose(actual_test_sheet["$S$41"].value, 30.836736147625416)
    assert_allclose(actual_test_sheet["$T$41"].value, 0.5002309375882134)
    assert_allclose(actual_test_sheet["$U$41"].value, 1147.5289114071275)
    assert_allclose(actual_test_sheet["$V$41"].value, 1.6461422021106258)
    assert_allclose(actual_test_sheet["$W$41"].value, 128.82560797648563)
    assert_allclose(actual_test_sheet["$X$41"].value, 0.045099110091540565)
    assert_allclose(actual_test_sheet["$Y$41"].value, 3383.747703278145)
    assert_allclose(actual_test_sheet["$Z$41"].value, 1.1845782262482565)
    assert_allclose(actual_test_sheet["$AA$41"].value, 0.47466777978262975)
    assert_allclose(actual_test_sheet["$F$42"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$43"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$44"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$45"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$46"].value, 10.0)
    assert actual_test_sheet["$F$47"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$47"].value, 1.3028967107354457)
    assert_allclose(actual_test_sheet["$H$47"].value, 1.0119667955440215)
    assert_allclose(actual_test_sheet["$I$47"].value, 0.5385977795294747)
    assert_allclose(actual_test_sheet["$J$47"].value, 0.004651125237953302)
    assert_allclose(actual_test_sheet["$K$47"].value, 11348733.149334429)
    assert_allclose(actual_test_sheet["$L$47"].value, 0.993111416726537)
    assert_allclose(actual_test_sheet["$M$47"].value, 0.012101752233049871)
    assert_allclose(actual_test_sheet["$N$47"].value, 1.0234268792944528)
    assert_allclose(actual_test_sheet["$O$47"].value, 247.3825479984152)
    assert_allclose(actual_test_sheet["$P$47"].value, 0.9877916786392555)
    assert actual_test_sheet["$Q$47"].value == " - "
    assert actual_test_sheet["$R$47"].value == " - "
    assert_allclose(actual_test_sheet["$S$47"].value, 60.005467349253166)
    assert_allclose(actual_test_sheet["$T$47"].value, 1.0143374900705107)
    assert_allclose(actual_test_sheet["$U$47"].value, 713.4328560410924)
    assert_allclose(actual_test_sheet["$V$47"].value, 1.0234268792944525)
    assert actual_test_sheet["$W$47"].value == " - "

    assert actual_test_sheet["$X$47"].value == " - "
    assert_allclose(actual_test_sheet["$Y$47"].value, 2809.3939165451848)
    assert_allclose(actual_test_sheet["$Z$47"].value, 0.9835091603518938)
    assert_allclose(actual_test_sheet["$AB$47"].value, 0.6969279216077816)


def test_2sec_reynolds():
    wb = xl.Book(beta_2section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$4"].value = "Yes"  # set reynolds
    actual_test_sheet["$C$8"].value = "No"  # set casing
    actual_test_sheet["$C$16"].value = "No"  # set casing
    actual_test_sheet["$C$26"].value = "No"  # set balance and divwall
    actual_test_sheet["$C$28"].value = "No"  # set buffer

    runpy.run_path(str(script_2sec), run_name="test_script")

    assert actual_test_sheet["$B$3"].value == "Opções"
    assert actual_test_sheet["$F$3"].value == "SECTION 1 - Tested points - Measurements"
    assert actual_test_sheet["$X$3"].value == "Ordenar por:"
    assert actual_test_sheet["$Y$3"].value == "Vazão Seção 1"
    assert (
        actual_test_sheet["$AD$3"].value == "SECTION 2 - Tested points - Measurements"
    )
    assert actual_test_sheet["$B$4"].value == "Reynolds correction"
    assert actual_test_sheet["$C$4"].value == "Yes"
    assert actual_test_sheet["$D$4"].value == "Rugosidade [in] - Case 1"
    assert actual_test_sheet["$G$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$H$4"].value, 3774.0)
    assert actual_test_sheet["$I$4"].value == "rpm"
    assert actual_test_sheet["$AE$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$AF$4"].value, 3774.0)
    assert actual_test_sheet["$AG$4"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$5"].value, 0.01)
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$M$5"].value == "Mbuf"
    assert actual_test_sheet["$N$5"].value == "Tbuf"
    assert actual_test_sheet["$O$5"].value == "Mbal"
    assert actual_test_sheet["$P$5"].value == "Pend"
    assert actual_test_sheet["$Q$5"].value == "Tend"
    assert actual_test_sheet["$R$5"].value == "Mdiv"
    assert actual_test_sheet["$S$5"].value == "Pdiv"
    assert actual_test_sheet["$T$5"].value == "Tdiv"
    assert actual_test_sheet["$U$5"].value == "Md1f"
    assert actual_test_sheet["$V$5"].value == "Gas Selection"
    assert actual_test_sheet["$W$5"].value == "Speed"
    assert actual_test_sheet["$AE$5"].value == "Ms"
    assert actual_test_sheet["$AF$5"].value == "Qs"
    assert actual_test_sheet["$AG$5"].value == "Ps"
    assert actual_test_sheet["$AH$5"].value == "Ts"
    assert actual_test_sheet["$AI$5"].value == "Pd"
    assert actual_test_sheet["$AJ$5"].value == "Td"
    assert actual_test_sheet["$AK$5"].value == "Mbal"
    assert actual_test_sheet["$AL$5"].value == "Mbuf"
    assert actual_test_sheet["$AM$5"].value == "Gas Selection"
    assert actual_test_sheet["$AN$5"].value == "Speed"
    assert actual_test_sheet["$D$6"].value == "Rugosidade [in] - Case 2"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$M$6"].value == "kg/s"
    assert actual_test_sheet["$N$6"].value == "kelvin"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "bar"
    assert actual_test_sheet["$Q$6"].value == "kelvin"
    assert actual_test_sheet["$R$6"].value == "kg/h"
    assert actual_test_sheet["$S$6"].value == "bar"
    assert actual_test_sheet["$T$6"].value == "kelvin"
    assert actual_test_sheet["$U$6"].value == "kg/s"
    assert actual_test_sheet["$W$6"].value == "rpm"
    assert actual_test_sheet["$AE$6"].value == "kg/s"
    assert actual_test_sheet["$AF$6"].value == "m³/h"
    assert actual_test_sheet["$AG$6"].value == "bar"
    assert actual_test_sheet["$AH$6"].value == "kelvin"
    assert actual_test_sheet["$AI$6"].value == "bar"
    assert actual_test_sheet["$AJ$6"].value == "kelvin"
    assert actual_test_sheet["$AK$6"].value == "kg/s"
    assert actual_test_sheet["$AL$6"].value == "kg/s"
    assert actual_test_sheet["$AN$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$7"].value, 0.01)
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 3.277)
    assert_allclose(actual_test_sheet["$H$7"].value, 1298.3249050526144)
    assert_allclose(actual_test_sheet["$I$7"].value, 5.038)
    assert_allclose(actual_test_sheet["$J$7"].value, 300.9)
    assert_allclose(actual_test_sheet["$K$7"].value, 15.04)
    assert_allclose(actual_test_sheet["$L$7"].value, 404.3)
    assert_allclose(actual_test_sheet["$M$7"].value, 0.06143)
    assert_allclose(actual_test_sheet["$N$7"].value, 301.0)
    assert_allclose(actual_test_sheet["$P$7"].value, 14.6)
    assert_allclose(actual_test_sheet["$Q$7"].value, 304.8)
    assert_allclose(actual_test_sheet["$S$7"].value, 26.27)
    assert_allclose(actual_test_sheet["$T$7"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$7"].value, 9123.0)
    assert actual_test_sheet["$Z$7"].value == "Status"
    assert_allclose(actual_test_sheet["$AD$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AE$7"].value, 2.075)
    assert_allclose(actual_test_sheet["$AF$7"].value, 322.5064631506056)
    assert_allclose(actual_test_sheet["$AG$7"].value, 12.52)
    assert_allclose(actual_test_sheet["$AH$7"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$7"].value, 18.88)
    assert_allclose(actual_test_sheet["$AJ$7"].value, 346.4)
    assert_allclose(actual_test_sheet["$AK$7"].value, 0.1211)
    assert_allclose(actual_test_sheet["$AL$7"].value, 0.06033)
    assert_allclose(actual_test_sheet["$AM$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$7"].value, 7399.0)
    assert actual_test_sheet["$B$8"].value == "Casing 1 heat loss"
    assert actual_test_sheet["$C$8"].value == "No"
    assert actual_test_sheet["$D$8"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 3.888)
    assert_allclose(actual_test_sheet["$H$8"].value, 1500.3234856434028)
    assert_allclose(actual_test_sheet["$I$8"].value, 5.16)
    assert_allclose(actual_test_sheet["$J$8"].value, 300.4)
    assert_allclose(actual_test_sheet["$K$8"].value, 15.07)
    assert_allclose(actual_test_sheet["$L$8"].value, 400.2)
    assert_allclose(actual_test_sheet["$M$8"].value, 0.06099)
    assert_allclose(actual_test_sheet["$N$8"].value, 300.6)
    assert_allclose(actual_test_sheet["$P$8"].value, 14.66)
    assert_allclose(actual_test_sheet["$Q$8"].value, 304.6)
    assert_allclose(actual_test_sheet["$S$8"].value, 25.99)
    assert_allclose(actual_test_sheet["$T$8"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$8"].value, 9071.0)
    assert_allclose(actual_test_sheet["$AD$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$AE$8"].value, 2.587)
    assert_allclose(actual_test_sheet["$AF$8"].value, 404.1501023257591)
    assert_allclose(actual_test_sheet["$AG$8"].value, 12.46)
    assert_allclose(actual_test_sheet["$AH$8"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$8"].value, 18.6)
    assert_allclose(actual_test_sheet["$AJ$8"].value, 344.1)
    assert_allclose(actual_test_sheet["$AK$8"].value, 0.1171)
    assert_allclose(actual_test_sheet["$AL$8"].value, 0.05892)
    assert_allclose(actual_test_sheet["$AM$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$8"].value, 7449.0)
    assert_allclose(actual_test_sheet["$D$9"].value, 5.5)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 4.325)
    assert_allclose(actual_test_sheet["$H$9"].value, 1656.259613599762)
    assert_allclose(actual_test_sheet["$I$9"].value, 5.182)
    assert_allclose(actual_test_sheet["$J$9"].value, 299.5)
    assert_allclose(actual_test_sheet["$K$9"].value, 14.95)
    assert_allclose(actual_test_sheet["$L$9"].value, 397.6)
    assert_allclose(actual_test_sheet["$M$9"].value, 0.0616)
    assert_allclose(actual_test_sheet["$N$9"].value, 299.7)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1625)
    assert_allclose(actual_test_sheet["$P$9"].value, 14.59)
    assert_allclose(actual_test_sheet["$Q$9"].value, 304.3)
    assert_allclose(actual_test_sheet["$S$9"].value, 26.15)
    assert_allclose(actual_test_sheet["$T$9"].value, 362.5)
    assert_allclose(actual_test_sheet["$U$9"].value, 4.8059)
    assert_allclose(actual_test_sheet["$V$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$9"].value, 9096.0)
    assert actual_test_sheet["$Z$9"].value == "Calculado"
    assert_allclose(actual_test_sheet["$AD$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$AE$9"].value, 3.3600000000000003)
    assert_allclose(actual_test_sheet["$AF$9"].value, 517.6023230905009)
    assert_allclose(actual_test_sheet["$AG$9"].value, 12.62)
    assert_allclose(actual_test_sheet["$AH$9"].value, 304.4)
    assert_allclose(actual_test_sheet["$AI$9"].value, 18.15)
    assert_allclose(actual_test_sheet["$AJ$9"].value, 339.9)
    assert_allclose(actual_test_sheet["$AK$9"].value, 0.1222)
    assert_allclose(actual_test_sheet["$AL$9"].value, 0.07412)
    assert_allclose(actual_test_sheet["$AM$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$9"].value, 7412.0)
    assert actual_test_sheet["$D$10"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 5.724)

    assert_allclose(actual_test_sheet["$H$10"].value, 2021.0086305580305)
    assert_allclose(actual_test_sheet["$I$10"].value, 5.592)
    assert_allclose(actual_test_sheet["$J$10"].value, 298.7)
    assert_allclose(actual_test_sheet["$K$10"].value, 14.78)
    assert_allclose(actual_test_sheet["$L$10"].value, 389.8)
    assert_allclose(actual_test_sheet["$M$10"].value, 0.05942)
    assert_allclose(actual_test_sheet["$N$10"].value, 299.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 14.27)
    assert_allclose(actual_test_sheet["$Q$10"].value, 304.1)
    assert_allclose(actual_test_sheet["$S$10"].value, 25.43)
    assert_allclose(actual_test_sheet["$T$10"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$10"].value, 9057.0)
    assert_allclose(actual_test_sheet["$AD$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$AE$10"].value, 4.105)
    assert_allclose(actual_test_sheet["$AF$10"].value, 628.8975623074246)
    assert_allclose(actual_test_sheet["$AG$10"].value, 12.69)
    assert_allclose(actual_test_sheet["$AH$10"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$10"].value, 16.78)
    assert_allclose(actual_test_sheet["$AJ$10"].value, 333.3)
    assert_allclose(actual_test_sheet["$AK$10"].value, 0.1079)
    assert_allclose(actual_test_sheet["$AL$10"].value, 0.06692)
    assert_allclose(actual_test_sheet["$AM$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$10"].value, 7330.0)
    assert_allclose(actual_test_sheet["$D$11"].value, 23.895)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 8.716)
    assert_allclose(actual_test_sheet["$H$11"].value, 2412.192118154552)
    assert_allclose(actual_test_sheet["$I$11"].value, 7.083)
    assert_allclose(actual_test_sheet["$J$11"].value, 298.9)
    assert_allclose(actual_test_sheet["$K$11"].value, 14.16)
    assert_allclose(actual_test_sheet["$L$11"].value, 377.1)
    assert_allclose(actual_test_sheet["$M$11"].value, 0.06504)
    assert_allclose(actual_test_sheet["$N$11"].value, 299.5)
    assert_allclose(actual_test_sheet["$P$11"].value, 13.1)
    assert_allclose(actual_test_sheet["$Q$11"].value, 303.5)
    assert_allclose(actual_test_sheet["$S$11"].value, 23.13)
    assert_allclose(actual_test_sheet["$T$11"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$11"].value, 9024.0)
    assert_allclose(actual_test_sheet["$AD$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$AE$11"].value, 4.9270000000000005)
    assert_allclose(actual_test_sheet["$AF$11"].value, 730.7765001154256)
    assert_allclose(actual_test_sheet["$AG$11"].value, 13.11)
    assert_allclose(actual_test_sheet["$AH$11"].value, 305.1)
    assert_allclose(actual_test_sheet["$AI$11"].value, 16.31)
    assert_allclose(actual_test_sheet["$AJ$11"].value, 335.1)
    assert_allclose(actual_test_sheet["$AK$11"].value, 0.1066)
    assert_allclose(actual_test_sheet["$AL$11"].value, 0.06367)
    assert_allclose(actual_test_sheet["$AM$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$11"].value, 7739.0)
    assert actual_test_sheet["$D$12"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$AD$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$AD$13"].value, 7.0)
    assert actual_test_sheet["$D$14"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$AD$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$15"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$AD$15"].value, 9.0)
    assert actual_test_sheet["$B$16"].value == "Casing 2 heat loss"
    assert actual_test_sheet["$C$16"].value == "No"
    assert actual_test_sheet["$D$16"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$AD$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$17"].value, 5.5)
    assert actual_test_sheet["$D$18"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$D$19"].value, 17.97)
    assert actual_test_sheet["$F$19"].value == "SECTION 1 - Tested points - Results"
    assert actual_test_sheet["$D$20"].value == "Ambient Temperature [ °C ]"
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
    assert actual_test_sheet["$AC$20"].value == "Mdiv (kg/h)"
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
    assert actual_test_sheet["$AC$21"].value == "Mdiv_sp"
    assert actual_test_sheet["$D$22"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 2.2254125053126814)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.013123464366914)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.6537022458531642)
    assert_allclose(actual_test_sheet["$J$22"].value, -0.002874637138687741)
    assert_allclose(actual_test_sheet["$K$22"].value, 1065720.5685238568)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.11859356895525477)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.019768609167195028)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.758705139247969)
    assert_allclose(actual_test_sheet["$O$22"].value, 139.60059138942896)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.024441119758046)
    assert_allclose(actual_test_sheet["$Q$22"].value, 70.59695674947551)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5809779675549773)
    assert_allclose(actual_test_sheet["$S$22"].value, 125.80555911200125)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.0353174046776605)
    assert_allclose(actual_test_sheet["$U$22"].value, 1729.456420067326)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.758705139247969)
    assert_allclose(actual_test_sheet["$W$22"].value, 294.5895197453652)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.061556202801129445)
    assert_allclose(actual_test_sheet["$Y$22"].value, 3610.5064667711968)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.7544364391355908)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.7853172355486385)
    assert_allclose(actual_test_sheet["$D$23"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 2.196532014999917)
    assert_allclose(actual_test_sheet["$H$23"].value, 0.9999755637739081)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.6507428270979058)
    assert_allclose(actual_test_sheet["$J$23"].value, -0.005834055893946144)
    assert_allclose(actual_test_sheet["$K$23"].value, 1089590.9262789434)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.12124986648954703)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.022975244557738462)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.8817735215465565)
    assert_allclose(actual_test_sheet["$O$23"].value, 137.70383777399917)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.0105220354736857)
    assert_allclose(actual_test_sheet["$Q$23"].value, 68.68900157856706)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.565276442044267)
    assert_allclose(actual_test_sheet["$S$23"].value, 123.77162252575538)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0185791145526883)
    assert_allclose(actual_test_sheet["$U$23"].value, 2009.9888599616459)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.8817735215465565)
    assert_allclose(actual_test_sheet["$W$23"].value, 335.98431545131984)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.07020588742531288)
    assert_allclose(actual_test_sheet["$Y$23"].value, 4080.083651607769)
    assert_allclose(actual_test_sheet["$Z$23"].value, 0.8525573378205422)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.7948669799622327)

    assert actual_test_sheet["$B$24"].value == "Curve Shape"
    assert actual_test_sheet["$C$24"].value == "No"
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 2.177620827286962)
    assert_allclose(actual_test_sheet["$H$24"].value, 0.9913662079959106)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.6535559724840474)
    assert_allclose(actual_test_sheet["$J$24"].value, -0.0030209105078045084)
    assert_allclose(actual_test_sheet["$K$24"].value, 1104133.840408922)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.12286820448603784)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.025293467001523705)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9707452477385319)
    assert_allclose(actual_test_sheet["$O$24"].value, 134.95024206987415)
    assert_allclose(actual_test_sheet["$P$24"].value, 0.9903151248981737)
    assert_allclose(actual_test_sheet["$Q$24"].value, 67.54548985918196)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5558659072961302)
    assert_allclose(actual_test_sheet["$S$24"].value, 121.03003045017725)
    assert_allclose(actual_test_sheet["$T$24"].value, 0.9960171704509543)
    assert_allclose(actual_test_sheet["$U$24"].value, 2212.7985090694706)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9707452477385319)
    assert_allclose(actual_test_sheet["$W$24"].value, 366.53233432875203)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.07658907460324552)
    assert_allclose(actual_test_sheet["$Y$24"].value, 4380.867829888391)
    assert_allclose(actual_test_sheet["$Z$24"].value, 0.9154079507466809)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.7970217530083975)
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.028362859987217)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9234162218454397)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.6524130555549584)
    assert_allclose(actual_test_sheet["$J$25"].value, -0.004163827436893475)
    assert_allclose(actual_test_sheet["$K$25"].value, 1195120.8418341428)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.13299325372150472)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.030996610253312327)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.1896278235638378)
    assert_allclose(actual_test_sheet["$O$25"].value, 124.24722405946405)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9117723934795923)
    assert_allclose(actual_test_sheet["$Q$25"].value, 61.103221332331145)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.5028492299844557)
    assert_allclose(actual_test_sheet["$S$25"].value, 110.4377474157814)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9088479304095117)
    assert_allclose(actual_test_sheet["$U$25"].value, 2711.7378946352073)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.1896278235638376)
    assert_allclose(actual_test_sheet["$W$25"].value, 448.32977045252676)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.09368112720240022)
    assert_allclose(actual_test_sheet["$Y$25"].value, 5004.606444933251)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.0457417817525652)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.7801285169022669)
    assert actual_test_sheet["$B$26"].value == "Balance line and div. wall leakage"
    assert actual_test_sheet["$C$26"].value == "No"
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 1.578450967616677)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.7185929389843275)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.6527016569242936)
    assert_allclose(actual_test_sheet["$J$26"].value, -0.0038752260675583017)
    assert_allclose(actual_test_sheet["$K$26"].value, 1516369.3458798889)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1687418427433828)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.037131561204681994)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.4250828713353563)
    assert_allclose(actual_test_sheet["$O$26"].value, 94.48335664916515)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.6933540518761659)
    assert_allclose(actual_test_sheet["$Q$26"].value, 42.57668472606889)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.3503850151099371)
    assert_allclose(actual_test_sheet["$S$26"].value, 77.69156348545519)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.6393630650415194)
    assert_allclose(actual_test_sheet["$U$26"].value, 3248.4539690898223)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.4250828713353563)
    assert_allclose(actual_test_sheet["$W$26"].value, 589.4175986646264)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.12316225393665012)
    assert_allclose(actual_test_sheet["$Y$26"].value, 5214.076803834694)
    assert_allclose(actual_test_sheet["$Z$26"].value, 1.08951183815005)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.6296018050922979)
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert actual_test_sheet["$B$28"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$28"].value == "No"
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert actual_test_sheet["$B$30"].value == "Variable Speed"
    assert actual_test_sheet["$C$30"].value == "Yes"
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 2.1209294432821553)
    assert_allclose(actual_test_sheet["$H$32"].value, 0.9655573427964966)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.6565768829918519)
    assert_allclose(actual_test_sheet["$K$32"].value, 8986326.812762942)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.02605572065425804)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$32"].value, 133.5197301199669)
    assert_allclose(actual_test_sheet["$P$32"].value, 0.9798174955600416)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 119.6447228125721)
    assert_allclose(actual_test_sheet["$T$32"].value, 0.9886433764218802)
    assert_allclose(actual_test_sheet["$U$32"].value, 2279.4842562705835)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 4470.80343470779)
    assert_allclose(actual_test_sheet["$Z$32"].value, 0.934200521283781)
    assert_allclose(actual_test_sheet["$AB$32"].value, 0.798380190354987)
    assert actual_test_sheet["$F$34"].value == "SECTION 2 - Tested points - Results"
    assert actual_test_sheet["$G$35"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$35"].value == "Mach"
    assert actual_test_sheet["$K$35"].value == "Reynolds"
    assert actual_test_sheet["$M$35"].value == "Flow Coef."
    assert actual_test_sheet["$O$35"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$35"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$35"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$35"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$35"].value == "Power (kW)"
    assert actual_test_sheet["$Y$35"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$35"].value == "Polytropic Eff."
    assert actual_test_sheet["$AC$35"].value == "Mdiv"
    assert actual_test_sheet["$F$36"].value == "ERRO!"
    assert actual_test_sheet["$G$36"].value == "vi/vd"
    assert actual_test_sheet["$H$36"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$36"].value == "Mt"
    assert actual_test_sheet["$J$36"].value == "Mt - Msp"
    assert actual_test_sheet["$K$36"].value == "Re_t"
    assert actual_test_sheet["$L$36"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$36"].value == "ft"
    assert actual_test_sheet["$N$36"].value == "ft/fsp"
    assert actual_test_sheet["$O$36"].value == "Pdconv"
    assert actual_test_sheet["$P$36"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$36"].value == "Ht"
    assert actual_test_sheet["$R$36"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$36"].value == "Hconv"
    assert actual_test_sheet["$T$36"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$36"].value == "Qconv"
    assert actual_test_sheet["$V$36"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$36"].value == "Wt"
    assert actual_test_sheet["$X$36"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$36"].value == "Wconv"
    assert actual_test_sheet["$Z$36"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$36"].value == "ht"
    assert actual_test_sheet["$AB$36"].value == "Reynolds corr."
    assert actual_test_sheet["$AC$36"].value == "kg/h"

    assert_allclose(actual_test_sheet["$F$37"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$37"].value, 1.3227207253089355)
    assert_allclose(actual_test_sheet["$H$37"].value, 1.027364212958199)
    assert_allclose(actual_test_sheet["$I$37"].value, 0.4719605160746876)
    assert_allclose(actual_test_sheet["$J$37"].value, -0.06198613821683385)
    assert_allclose(actual_test_sheet["$K$37"].value, 1192374.3898159557)
    assert_allclose(actual_test_sheet["$L$37"].value, 0.1043429785471704)
    assert_allclose(actual_test_sheet["$M$37"].value, 0.008985131877381945)
    assert_allclose(actual_test_sheet["$N$37"].value, 0.7598590105162515)
    assert_allclose(actual_test_sheet["$O$37"].value, 256.4933836362484)
    assert_allclose(actual_test_sheet["$P$37"].value, 1.0241709935962642)
    assert_allclose(actual_test_sheet["$Q$37"].value, 23.729875113017336)
    assert_allclose(actual_test_sheet["$R$37"].value, 0.3849440362238192)
    assert_allclose(actual_test_sheet["$S$37"].value, 64.2533804914097)
    assert_allclose(actual_test_sheet["$T$37"].value, 1.042312928727548)
    assert_allclose(actual_test_sheet["$U$37"].value, 529.6991851874122)
    assert_allclose(actual_test_sheet["$V$37"].value, 0.7598590105162514)
    assert_allclose(actual_test_sheet["$W$37"].value, 72.4141177108613)
    assert_allclose(actual_test_sheet["$X$37"].value, 0.025350645093947594)
    assert_allclose(actual_test_sheet["$Y$37"].value, 2281.886496692945)
    assert_allclose(actual_test_sheet["$Z$37"].value, 0.7988400128454209)
    assert_allclose(actual_test_sheet["$AA$37"].value, 0.679970873305629)
    assert_allclose(actual_test_sheet["$F$38"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$38"].value, 1.3192737459068735)
    assert_allclose(actual_test_sheet["$H$38"].value, 1.0246869257480393)
    assert_allclose(actual_test_sheet["$I$38"].value, 0.47506645243163736)
    assert_allclose(actual_test_sheet["$J$38"].value, -0.058880201859884074)
    assert_allclose(actual_test_sheet["$K$38"].value, 1194368.5372530876)
    assert_allclose(actual_test_sheet["$L$38"].value, 0.10451748353908377)
    assert_allclose(actual_test_sheet["$M$38"].value, 0.011184170506366536)
    assert_allclose(actual_test_sheet["$N$38"].value, 0.9458283807503725)
    assert_allclose(actual_test_sheet["$O$38"].value, 251.03797625043703)
    assert_allclose(actual_test_sheet["$P$38"].value, 1.0023877026450927)
    assert_allclose(actual_test_sheet["$Q$38"].value, 23.06263900998732)
    assert_allclose(actual_test_sheet["$R$38"].value, 0.3741201883362368)
    assert_allclose(actual_test_sheet["$S$38"].value, 61.586990548307874)
    assert_allclose(actual_test_sheet["$T$38"].value, 0.9990589755585672)
    assert_allclose(actual_test_sheet["$U$38"].value, 659.3387926928933)
    assert_allclose(actual_test_sheet["$V$38"].value, 0.9458283807503722)
    assert_allclose(actual_test_sheet["$W$38"].value, 84.84249462742811)
    assert_allclose(actual_test_sheet["$X$38"].value, 0.029701555969693018)
    assert_allclose(actual_test_sheet["$Y$38"].value, 2633.5121504794356)
    assert_allclose(actual_test_sheet["$Z$38"].value, 0.9219366884226976)
    assert_allclose(actual_test_sheet["$AA$38"].value, 0.7032212735002392)
    assert_allclose(actual_test_sheet["$F$39"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$39"].value, 1.2866731198277017)
    assert_allclose(actual_test_sheet["$H$39"].value, 0.9993658463146237)
    assert_allclose(actual_test_sheet["$I$39"].value, 0.4730184033476288)
    assert_allclose(actual_test_sheet["$J$39"].value, -0.06092825094389265)
    assert_allclose(actual_test_sheet["$K$39"].value, 1205399.4462691715)
    assert_allclose(actual_test_sheet["$L$39"].value, 0.10548278262018757)
    assert_allclose(actual_test_sheet["$M$39"].value, 0.014395271717545245)
    assert_allclose(actual_test_sheet["$N$39"].value, 1.2173863525522004)
    assert_allclose(actual_test_sheet["$O$39"].value, 239.05824137377022)
    assert_allclose(actual_test_sheet["$P$39"].value, 0.9545529522990346)
    assert_allclose(actual_test_sheet["$Q$39"].value, 20.761393895089576)
    assert_allclose(actual_test_sheet["$R$39"].value, 0.336789583828203)
    assert_allclose(actual_test_sheet["$S$39"].value, 55.988968488592946)
    assert_allclose(actual_test_sheet["$T$39"].value, 0.9082483330131064)
    assert_allclose(actual_test_sheet["$U$39"].value, 848.6423798107802)
    assert_allclose(actual_test_sheet["$V$39"].value, 1.2173863525522002)
    assert_allclose(actual_test_sheet["$W$39"].value, 98.3947687725241)
    assert_allclose(actual_test_sheet["$X$39"].value, 0.03444591940224894)
    assert_allclose(actual_test_sheet["$Y$39"].value, 3056.9777114242056)
    assert_allclose(actual_test_sheet["$Z$39"].value, 1.0701829901712605)
    assert_allclose(actual_test_sheet["$AA$39"].value, 0.7089633357315271)
    assert_allclose(actual_test_sheet["$F$40"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$40"].value, 1.2056421414082092)
    assert_allclose(actual_test_sheet["$H$40"].value, 0.9364286549814107)
    assert_allclose(actual_test_sheet["$I$40"].value, 0.46779210993261205)
    assert_allclose(actual_test_sheet["$J$40"].value, -0.06615454435890938)
    assert_allclose(actual_test_sheet["$K$40"].value, 1198177.4782408962)
    assert_allclose(actual_test_sheet["$L$40"].value, 0.10485079852066409)
    assert_allclose(actual_test_sheet["$M$40"].value, 0.017686218956384073)
    assert_allclose(actual_test_sheet["$N$40"].value, 1.4956967821253158)
    assert_allclose(actual_test_sheet["$O$40"].value, 212.9060543444797)
    assert_allclose(actual_test_sheet["$P$40"].value, 0.8501279921118021)
    assert_allclose(actual_test_sheet["$Q$40"].value, 15.807602800854134)
    assert_allclose(actual_test_sheet["$R$40"].value, 0.2564296017658226)
    assert_allclose(actual_test_sheet["$S$40"].value, 43.625137899496146)
    assert_allclose(actual_test_sheet["$T$40"].value, 0.7076833141292261)
    assert_allclose(actual_test_sheet["$U$40"].value, 1042.653118294857)
    assert_allclose(actual_test_sheet["$V$40"].value, 1.4956967821253153)
    assert_allclose(actual_test_sheet["$W$40"].value, 98.17569085850735)
    assert_allclose(actual_test_sheet["$X$40"].value, 0.03436922487607469)
    assert_allclose(actual_test_sheet["$Y$40"].value, 3136.377627790204)
    assert_allclose(actual_test_sheet["$Z$40"].value, 1.0979792150499577)
    assert_allclose(actual_test_sheet["$AA$40"].value, 0.6609600495811861)
    assert_allclose(actual_test_sheet["$F$41"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$41"].value, 1.1250598933659246)
    assert_allclose(actual_test_sheet["$H$41"].value, 0.8738399949155996)
    assert_allclose(actual_test_sheet["$I$41"].value, 0.493933640164255)
    assert_allclose(actual_test_sheet["$J$41"].value, -0.04001301412726643)
    assert_allclose(actual_test_sheet["$K$41"].value, 1303631.450002704)
    assert_allclose(actual_test_sheet["$L$41"].value, 0.11407892486020633)
    assert_allclose(actual_test_sheet["$M$41"].value, 0.019465196266921888)
    assert_allclose(actual_test_sheet["$N$41"].value, 1.646142202110626)
    assert_allclose(actual_test_sheet["$O$41"].value, 186.66732309735139)
    assert_allclose(actual_test_sheet["$P$41"].value, 0.7453574632540784)
    assert_allclose(actual_test_sheet["$Q$41"].value, 12.411074754890574)
    assert_allclose(actual_test_sheet["$R$41"].value, 0.20133140976381822)
    assert_allclose(actual_test_sheet["$S$41"].value, 30.83208507202277)
    assert_allclose(actual_test_sheet["$T$41"].value, 0.5001554882313695)
    assert_allclose(actual_test_sheet["$U$41"].value, 1147.5289114071275)
    assert_allclose(actual_test_sheet["$V$41"].value, 1.6461422021106258)
    assert_allclose(actual_test_sheet["$W$41"].value, 127.48145197648562)
    assert_allclose(actual_test_sheet["$X$41"].value, 0.04462854961543344)
    assert_allclose(actual_test_sheet["$Y$41"].value, 3350.1482630749633)
    assert_allclose(actual_test_sheet["$Z$41"].value, 1.172815775625753)
    assert_allclose(actual_test_sheet["$AA$41"].value, 0.4796726454655151)
    assert_allclose(actual_test_sheet["$F$42"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$43"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$44"].value, 8.0)
    assert_allclose(actual_test_sheet["$F$45"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$46"].value, 10.0)
    assert actual_test_sheet["$F$47"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$47"].value, 1.3057262090225201)
    assert_allclose(actual_test_sheet["$H$47"].value, 1.0141644818924287)
    assert_allclose(actual_test_sheet["$I$47"].value, 0.5384985005898867)
    assert_allclose(actual_test_sheet["$J$47"].value, 0.0045518462983652475)
    assert_allclose(actual_test_sheet["$K$47"].value, 11350515.946256503)
    assert_allclose(actual_test_sheet["$L$47"].value, 0.993267426736969)
    assert_allclose(actual_test_sheet["$M$47"].value, 0.012095588522295248)
    assert_allclose(actual_test_sheet["$N$47"].value, 1.0229056236001535)
    assert_allclose(actual_test_sheet["$O$47"].value, 247.63772646863842)
    assert_allclose(actual_test_sheet["$P$47"].value, 0.9888105992199265)
    assert actual_test_sheet["$Q$47"].value == " - "
    assert actual_test_sheet["$R$47"].value == " - "
    assert_allclose(actual_test_sheet["$S$47"].value, 60.00613002900408)
    assert_allclose(actual_test_sheet["$T$47"].value, 1.0143486920650113)
    assert_allclose(actual_test_sheet["$U$47"].value, 713.0694876889067)
    assert_allclose(actual_test_sheet["$V$47"].value, 1.0229056236001532)
    assert actual_test_sheet["$W$47"].value == " - "
    assert actual_test_sheet["$X$47"].value == " - "
    assert_allclose(actual_test_sheet["$Y$47"].value, 2767.6630470758855)
    assert_allclose(actual_test_sheet["$Z$47"].value, 0.9689000689920831)
    assert_allclose(actual_test_sheet["$AB$47"].value, 0.7074440250868492)


def test_2sec():
    wb = xl.Book(beta_2section)
    wb.app.visible = True
    actual_test_sheet = wb.sheets["Actual Test Data"]
    actual_test_sheet["$C$4"].value = "No"  # set reynolds
    actual_test_sheet["$C$8"].value = "No"  # set casing
    actual_test_sheet["$C$16"].value = "No"  # set casing
    actual_test_sheet["$C$26"].value = "No"  # set balance and divwall
    actual_test_sheet["$C$28"].value = "No"  # set buffer

    runpy.run_path(str(script_2sec), run_name="test_script")

    assert actual_test_sheet["$B$3"].value == "Opções"
    assert actual_test_sheet["$F$3"].value == "SECTION 1 - Tested points - Measurements"
    assert actual_test_sheet["$X$3"].value == "Ordenar por:"
    assert actual_test_sheet["$Y$3"].value == "Vazão Seção 1"
    assert (
        actual_test_sheet["$AD$3"].value == "SECTION 2 - Tested points - Measurements"
    )
    assert actual_test_sheet["$B$4"].value == "Reynolds correction"
    assert actual_test_sheet["$C$4"].value == "No"
    assert actual_test_sheet["$D$4"].value == "Rugosidade [in] - Case 1"
    assert actual_test_sheet["$G$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$H$4"].value, 3774.0)
    assert actual_test_sheet["$I$4"].value == "rpm"
    assert actual_test_sheet["$AE$4"].value == "Speed"
    assert_allclose(actual_test_sheet["$AF$4"].value, 3774.0)
    assert actual_test_sheet["$AG$4"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$5"].value, 0.01)
    assert actual_test_sheet["$G$5"].value == "Ms"
    assert actual_test_sheet["$H$5"].value == "Qs"
    assert actual_test_sheet["$I$5"].value == "Ps"
    assert actual_test_sheet["$J$5"].value == "Ts"
    assert actual_test_sheet["$K$5"].value == "Pd"
    assert actual_test_sheet["$L$5"].value == "Td"
    assert actual_test_sheet["$M$5"].value == "Mbuf"
    assert actual_test_sheet["$N$5"].value == "Tbuf"
    assert actual_test_sheet["$O$5"].value == "Mbal"
    assert actual_test_sheet["$P$5"].value == "Pend"
    assert actual_test_sheet["$Q$5"].value == "Tend"
    assert actual_test_sheet["$R$5"].value == "Mdiv"
    assert actual_test_sheet["$S$5"].value == "Pdiv"
    assert actual_test_sheet["$T$5"].value == "Tdiv"
    assert actual_test_sheet["$U$5"].value == "Md1f"
    assert actual_test_sheet["$V$5"].value == "Gas Selection"
    assert actual_test_sheet["$W$5"].value == "Speed"
    assert actual_test_sheet["$AE$5"].value == "Ms"
    assert actual_test_sheet["$AF$5"].value == "Qs"
    assert actual_test_sheet["$AG$5"].value == "Ps"
    assert actual_test_sheet["$AH$5"].value == "Ts"
    assert actual_test_sheet["$AI$5"].value == "Pd"
    assert actual_test_sheet["$AJ$5"].value == "Td"
    assert actual_test_sheet["$AK$5"].value == "Mbal"
    assert actual_test_sheet["$AL$5"].value == "Mbuf"
    assert actual_test_sheet["$AM$5"].value == "Gas Selection"
    assert actual_test_sheet["$AN$5"].value == "Speed"
    assert actual_test_sheet["$D$6"].value == "Rugosidade [in] - Case 2"
    assert actual_test_sheet["$G$6"].value == "kg/s"
    assert actual_test_sheet["$H$6"].value == "m³/h"
    assert actual_test_sheet["$I$6"].value == "bar"
    assert actual_test_sheet["$J$6"].value == "kelvin"
    assert actual_test_sheet["$K$6"].value == "bar"
    assert actual_test_sheet["$L$6"].value == "kelvin"
    assert actual_test_sheet["$M$6"].value == "kg/s"
    assert actual_test_sheet["$N$6"].value == "kelvin"
    assert actual_test_sheet["$O$6"].value == "kg/s"
    assert actual_test_sheet["$P$6"].value == "bar"
    assert actual_test_sheet["$Q$6"].value == "kelvin"
    assert actual_test_sheet["$R$6"].value == "kg/h"
    assert actual_test_sheet["$S$6"].value == "bar"
    assert actual_test_sheet["$T$6"].value == "kelvin"
    assert actual_test_sheet["$U$6"].value == "kg/s"
    assert actual_test_sheet["$W$6"].value == "rpm"
    assert actual_test_sheet["$AE$6"].value == "kg/s"
    assert actual_test_sheet["$AF$6"].value == "m³/h"
    assert actual_test_sheet["$AG$6"].value == "bar"
    assert actual_test_sheet["$AH$6"].value == "kelvin"
    assert actual_test_sheet["$AI$6"].value == "bar"
    assert actual_test_sheet["$AJ$6"].value == "kelvin"
    assert actual_test_sheet["$AK$6"].value == "kg/s"
    assert actual_test_sheet["$AL$6"].value == "kg/s"
    assert actual_test_sheet["$AN$6"].value == "rpm"
    assert_allclose(actual_test_sheet["$D$7"].value, 0.01)
    assert_allclose(actual_test_sheet["$F$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$7"].value, 3.277)
    assert_allclose(actual_test_sheet["$H$7"].value, 1298.3249050526144)
    assert_allclose(actual_test_sheet["$I$7"].value, 5.038)
    assert_allclose(actual_test_sheet["$J$7"].value, 300.9)
    assert_allclose(actual_test_sheet["$K$7"].value, 15.04)
    assert_allclose(actual_test_sheet["$L$7"].value, 404.3)
    assert_allclose(actual_test_sheet["$M$7"].value, 0.06143)
    assert_allclose(actual_test_sheet["$N$7"].value, 301.0)
    assert_allclose(actual_test_sheet["$P$7"].value, 14.6)
    assert_allclose(actual_test_sheet["$Q$7"].value, 304.8)
    assert_allclose(actual_test_sheet["$S$7"].value, 26.27)
    assert_allclose(actual_test_sheet["$T$7"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$7"].value, 9123.0)
    assert actual_test_sheet["$Z$7"].value == "Status"
    assert_allclose(actual_test_sheet["$AD$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AE$7"].value, 2.075)
    assert_allclose(actual_test_sheet["$AF$7"].value, 322.5064631506056)
    assert_allclose(actual_test_sheet["$AG$7"].value, 12.52)
    assert_allclose(actual_test_sheet["$AH$7"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$7"].value, 18.88)
    assert_allclose(actual_test_sheet["$AJ$7"].value, 346.4)
    assert_allclose(actual_test_sheet["$AK$7"].value, 0.1211)
    assert_allclose(actual_test_sheet["$AL$7"].value, 0.06033)
    assert_allclose(actual_test_sheet["$AM$7"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$7"].value, 7399.0)
    assert actual_test_sheet["$B$8"].value == "Casing 1 heat loss"
    assert actual_test_sheet["$C$8"].value == "No"
    assert actual_test_sheet["$D$8"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$8"].value, 3.888)
    assert_allclose(actual_test_sheet["$H$8"].value, 1500.3234856434028)
    assert_allclose(actual_test_sheet["$I$8"].value, 5.16)
    assert_allclose(actual_test_sheet["$J$8"].value, 300.4)
    assert_allclose(actual_test_sheet["$K$8"].value, 15.07)
    assert_allclose(actual_test_sheet["$L$8"].value, 400.2)
    assert_allclose(actual_test_sheet["$M$8"].value, 0.06099)
    assert_allclose(actual_test_sheet["$N$8"].value, 300.6)
    assert_allclose(actual_test_sheet["$P$8"].value, 14.66)
    assert_allclose(actual_test_sheet["$Q$8"].value, 304.6)
    assert_allclose(actual_test_sheet["$S$8"].value, 25.99)
    assert_allclose(actual_test_sheet["$T$8"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$8"].value, 9071.0)
    assert_allclose(actual_test_sheet["$AD$8"].value, 2.0)
    assert_allclose(actual_test_sheet["$AE$8"].value, 2.587)
    assert_allclose(actual_test_sheet["$AF$8"].value, 404.1501023257591)
    assert_allclose(actual_test_sheet["$AG$8"].value, 12.46)
    assert_allclose(actual_test_sheet["$AH$8"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$8"].value, 18.6)
    assert_allclose(actual_test_sheet["$AJ$8"].value, 344.1)
    assert_allclose(actual_test_sheet["$AK$8"].value, 0.1171)
    assert_allclose(actual_test_sheet["$AL$8"].value, 0.05892)
    assert_allclose(actual_test_sheet["$AM$8"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$8"].value, 7449.0)
    assert_allclose(actual_test_sheet["$D$9"].value, 5.5)
    assert_allclose(actual_test_sheet["$F$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$9"].value, 4.325)
    assert_allclose(actual_test_sheet["$H$9"].value, 1656.259613599762)
    assert_allclose(actual_test_sheet["$I$9"].value, 5.182)
    assert_allclose(actual_test_sheet["$J$9"].value, 299.5)
    assert_allclose(actual_test_sheet["$K$9"].value, 14.95)
    assert_allclose(actual_test_sheet["$L$9"].value, 397.6)
    assert_allclose(actual_test_sheet["$M$9"].value, 0.0616)
    assert_allclose(actual_test_sheet["$N$9"].value, 299.7)
    assert_allclose(actual_test_sheet["$O$9"].value, 0.1625)
    assert_allclose(actual_test_sheet["$P$9"].value, 14.59)
    assert_allclose(actual_test_sheet["$Q$9"].value, 304.3)
    assert_allclose(actual_test_sheet["$S$9"].value, 26.15)
    assert_allclose(actual_test_sheet["$T$9"].value, 362.5)
    assert_allclose(actual_test_sheet["$U$9"].value, 4.8059)
    assert_allclose(actual_test_sheet["$V$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$9"].value, 9096.0)
    assert actual_test_sheet["$Z$9"].value == "Calculado"
    assert_allclose(actual_test_sheet["$AD$9"].value, 3.0)
    assert_allclose(actual_test_sheet["$AE$9"].value, 3.3600000000000003)
    assert_allclose(actual_test_sheet["$AF$9"].value, 517.6023230905009)
    assert_allclose(actual_test_sheet["$AG$9"].value, 12.62)
    assert_allclose(actual_test_sheet["$AH$9"].value, 304.4)
    assert_allclose(actual_test_sheet["$AI$9"].value, 18.15)
    assert_allclose(actual_test_sheet["$AJ$9"].value, 339.9)
    assert_allclose(actual_test_sheet["$AK$9"].value, 0.1222)
    assert_allclose(actual_test_sheet["$AL$9"].value, 0.07412)
    assert_allclose(actual_test_sheet["$AM$9"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$9"].value, 7412.0)
    assert actual_test_sheet["$D$10"].value == "Casing temperature* [ °C ]"

    assert_allclose(actual_test_sheet["$F$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$10"].value, 5.724)
    assert_allclose(actual_test_sheet["$H$10"].value, 2021.0086305580305)
    assert_allclose(actual_test_sheet["$I$10"].value, 5.592)
    assert_allclose(actual_test_sheet["$J$10"].value, 298.7)
    assert_allclose(actual_test_sheet["$K$10"].value, 14.78)
    assert_allclose(actual_test_sheet["$L$10"].value, 389.8)
    assert_allclose(actual_test_sheet["$M$10"].value, 0.05942)
    assert_allclose(actual_test_sheet["$N$10"].value, 299.1)
    assert_allclose(actual_test_sheet["$P$10"].value, 14.27)
    assert_allclose(actual_test_sheet["$Q$10"].value, 304.1)
    assert_allclose(actual_test_sheet["$S$10"].value, 25.43)
    assert_allclose(actual_test_sheet["$T$10"].value, 363.7)
    assert_allclose(actual_test_sheet["$V$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$10"].value, 9057.0)
    assert_allclose(actual_test_sheet["$AD$10"].value, 4.0)
    assert_allclose(actual_test_sheet["$AE$10"].value, 4.105)
    assert_allclose(actual_test_sheet["$AF$10"].value, 628.8975623074246)
    assert_allclose(actual_test_sheet["$AG$10"].value, 12.69)
    assert_allclose(actual_test_sheet["$AH$10"].value, 304.5)
    assert_allclose(actual_test_sheet["$AI$10"].value, 16.78)
    assert_allclose(actual_test_sheet["$AJ$10"].value, 333.3)
    assert_allclose(actual_test_sheet["$AK$10"].value, 0.1079)
    assert_allclose(actual_test_sheet["$AL$10"].value, 0.06692)
    assert_allclose(actual_test_sheet["$AM$10"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$10"].value, 7330.0)
    assert_allclose(actual_test_sheet["$D$11"].value, 23.895)
    assert_allclose(actual_test_sheet["$F$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$11"].value, 8.716)
    assert_allclose(actual_test_sheet["$H$11"].value, 2412.192118154552)
    assert_allclose(actual_test_sheet["$I$11"].value, 7.083)
    assert_allclose(actual_test_sheet["$J$11"].value, 298.9)
    assert_allclose(actual_test_sheet["$K$11"].value, 14.16)
    assert_allclose(actual_test_sheet["$L$11"].value, 377.1)
    assert_allclose(actual_test_sheet["$M$11"].value, 0.06504)
    assert_allclose(actual_test_sheet["$N$11"].value, 299.5)
    assert_allclose(actual_test_sheet["$P$11"].value, 13.1)
    assert_allclose(actual_test_sheet["$Q$11"].value, 303.5)
    assert_allclose(actual_test_sheet["$S$11"].value, 23.13)
    assert_allclose(actual_test_sheet["$T$11"].value, 361.8)
    assert_allclose(actual_test_sheet["$V$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$W$11"].value, 9024.0)
    assert_allclose(actual_test_sheet["$AD$11"].value, 5.0)
    assert_allclose(actual_test_sheet["$AE$11"].value, 4.9270000000000005)
    assert_allclose(actual_test_sheet["$AF$11"].value, 730.7765001154256)
    assert_allclose(actual_test_sheet["$AG$11"].value, 13.11)
    assert_allclose(actual_test_sheet["$AH$11"].value, 305.1)
    assert_allclose(actual_test_sheet["$AI$11"].value, 16.31)
    assert_allclose(actual_test_sheet["$AJ$11"].value, 335.1)
    assert_allclose(actual_test_sheet["$AK$11"].value, 0.1066)
    assert_allclose(actual_test_sheet["$AL$11"].value, 0.06367)
    assert_allclose(actual_test_sheet["$AM$11"].value, 1.0)
    assert_allclose(actual_test_sheet["$AN$11"].value, 7739.0)
    assert actual_test_sheet["$D$12"].value == "Ambient Temperature [ °C ]"
    assert_allclose(actual_test_sheet["$F$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$AD$12"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$13"].value, 7.0)
    assert_allclose(actual_test_sheet["$AD$13"].value, 7.0)
    assert actual_test_sheet["$D$14"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$AD$14"].value, 8.0)
    assert_allclose(actual_test_sheet["$D$15"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$15"].value, 9.0)
    assert_allclose(actual_test_sheet["$AD$15"].value, 9.0)
    assert actual_test_sheet["$B$16"].value == "Casing 2 heat loss"
    assert actual_test_sheet["$C$16"].value == "No"
    assert actual_test_sheet["$D$16"].value == "Casing area [m²]"
    assert_allclose(actual_test_sheet["$F$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$AD$16"].value, 10.0)
    assert_allclose(actual_test_sheet["$D$17"].value, 5.5)
    assert actual_test_sheet["$D$18"].value == "Casing temperature* [ °C ]"
    assert_allclose(actual_test_sheet["$D$19"].value, 17.97)
    assert actual_test_sheet["$F$19"].value == "SECTION 1 - Tested points - Results"
    assert actual_test_sheet["$D$20"].value == "Ambient Temperature [ °C ]"
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
    assert actual_test_sheet["$AC$20"].value == "Mdiv (kg/h)"
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
    assert actual_test_sheet["$AC$21"].value == "Mdiv_sp"
    assert actual_test_sheet["$D$22"].value == "Heat T. Constant [W/m²k]"
    assert_allclose(actual_test_sheet["$F$22"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$22"].value, 2.2254125053126814)
    assert_allclose(actual_test_sheet["$H$22"].value, 1.013123464366914)
    assert_allclose(actual_test_sheet["$I$22"].value, 0.6537022458531642)
    assert_allclose(actual_test_sheet["$J$22"].value, -0.002874637138687741)
    assert_allclose(actual_test_sheet["$K$22"].value, 1065720.5685238568)
    assert_allclose(actual_test_sheet["$L$22"].value, 0.11859356895525477)
    assert_allclose(actual_test_sheet["$M$22"].value, 0.019768609167195028)
    assert_allclose(actual_test_sheet["$N$22"].value, 0.758705139247969)
    assert_allclose(actual_test_sheet["$O$22"].value, 138.9718900723047)
    assert_allclose(actual_test_sheet["$P$22"].value, 1.0198274753966734)
    assert_allclose(actual_test_sheet["$Q$22"].value, 70.59695674947551)
    assert_allclose(actual_test_sheet["$R$22"].value, 0.5809779675549773)
    assert_allclose(actual_test_sheet["$S$22"].value, 125.2675118037012)
    assert_allclose(actual_test_sheet["$T$22"].value, 1.0308895419762432)
    assert_allclose(actual_test_sheet["$U$22"].value, 1729.456420067326)
    assert_allclose(actual_test_sheet["$V$22"].value, 0.758705139247969)
    assert_allclose(actual_test_sheet["$W$22"].value, 294.5895197453652)
    assert_allclose(actual_test_sheet["$X$22"].value, 0.061556202801129445)
    assert_allclose(actual_test_sheet["$Y$22"].value, 3610.506466771197)
    assert_allclose(actual_test_sheet["$Z$22"].value, 0.7544364391355909)
    assert_allclose(actual_test_sheet["$AA$22"].value, 0.7853172355486385)
    assert_allclose(actual_test_sheet["$D$23"].value, 13.6)
    assert_allclose(actual_test_sheet["$F$23"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$23"].value, 2.196532014999917)
    assert_allclose(actual_test_sheet["$H$23"].value, 0.9999755637739081)
    assert_allclose(actual_test_sheet["$I$23"].value, 0.6507428270979058)
    assert_allclose(actual_test_sheet["$J$23"].value, -0.005834055893946144)
    assert_allclose(actual_test_sheet["$K$23"].value, 1089590.9262789434)
    assert_allclose(actual_test_sheet["$L$23"].value, 0.12124986648954703)
    assert_allclose(actual_test_sheet["$M$23"].value, 0.022975244557738462)
    assert_allclose(actual_test_sheet["$N$23"].value, 0.8817735215465565)
    assert_allclose(actual_test_sheet["$O$23"].value, 137.13859067996998)
    assert_allclose(actual_test_sheet["$P$23"].value, 1.006374041828502)
    assert_allclose(actual_test_sheet["$Q$23"].value, 68.68900157856706)
    assert_allclose(actual_test_sheet["$R$23"].value, 0.565276442044267)
    assert_allclose(actual_test_sheet["$S$23"].value, 123.2834248147823)
    assert_allclose(actual_test_sheet["$T$23"].value, 1.0145614893327708)
    assert_allclose(actual_test_sheet["$U$23"].value, 2009.9888599616459)
    assert_allclose(actual_test_sheet["$V$23"].value, 0.8817735215465565)
    assert_allclose(actual_test_sheet["$W$23"].value, 335.98431545131984)
    assert_allclose(actual_test_sheet["$X$23"].value, 0.07020588742531288)
    assert_allclose(actual_test_sheet["$Y$23"].value, 4080.083651607769)
    assert_allclose(actual_test_sheet["$Z$23"].value, 0.8525573378205422)
    assert_allclose(actual_test_sheet["$AA$23"].value, 0.7948669799622327)

    assert actual_test_sheet["$B$24"].value == "Curve Shape"
    assert actual_test_sheet["$C$24"].value == "No"
    assert_allclose(actual_test_sheet["$F$24"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$24"].value, 2.177620827286962)
    assert_allclose(actual_test_sheet["$H$24"].value, 0.9913662079959106)
    assert_allclose(actual_test_sheet["$I$24"].value, 0.6535559724840474)
    assert_allclose(actual_test_sheet["$J$24"].value, -0.0030209105078045084)
    assert_allclose(actual_test_sheet["$K$24"].value, 1104133.840408922)
    assert_allclose(actual_test_sheet["$L$24"].value, 0.12286820448603784)
    assert_allclose(actual_test_sheet["$M$24"].value, 0.025293467001523705)
    assert_allclose(actual_test_sheet["$N$24"].value, 0.9707452477385319)
    assert_allclose(actual_test_sheet["$O$24"].value, 134.42072213785255)
    assert_allclose(actual_test_sheet["$P$24"].value, 0.9864293104707752)
    assert_allclose(actual_test_sheet["$Q$24"].value, 67.54548985918196)
    assert_allclose(actual_test_sheet["$R$24"].value, 0.5558659072961302)
    assert_allclose(actual_test_sheet["$S$24"].value, 120.56556148113086)
    assert_allclose(actual_test_sheet["$T$24"].value, 0.9921948210175853)
    assert_allclose(actual_test_sheet["$U$24"].value, 2212.7985090694706)
    assert_allclose(actual_test_sheet["$V$24"].value, 0.9707452477385319)
    assert_allclose(actual_test_sheet["$W$24"].value, 366.53233432875203)
    assert_allclose(actual_test_sheet["$X$24"].value, 0.07658907460324552)
    assert_allclose(actual_test_sheet["$Y$24"].value, 4380.867829888391)
    assert_allclose(actual_test_sheet["$Z$24"].value, 0.9154079507466809)
    assert_allclose(actual_test_sheet["$AA$24"].value, 0.7970217530083975)
    assert_allclose(actual_test_sheet["$F$25"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$25"].value, 2.028362859987217)
    assert_allclose(actual_test_sheet["$H$25"].value, 0.9234162218454397)
    assert_allclose(actual_test_sheet["$I$25"].value, 0.6524130555549584)
    assert_allclose(actual_test_sheet["$J$25"].value, -0.004163827436893475)
    assert_allclose(actual_test_sheet["$K$25"].value, 1195120.8418341428)
    assert_allclose(actual_test_sheet["$L$25"].value, 0.13299325372150472)
    assert_allclose(actual_test_sheet["$M$25"].value, 0.030996610253312327)
    assert_allclose(actual_test_sheet["$N$25"].value, 1.1896278235638378)
    assert_allclose(actual_test_sheet["$O$25"].value, 123.78907590161107)
    assert_allclose(actual_test_sheet["$P$25"].value, 0.9084103317062527)
    assert_allclose(actual_test_sheet["$Q$25"].value, 61.103221332331145)
    assert_allclose(actual_test_sheet["$R$25"].value, 0.5028492299844557)
    assert_allclose(actual_test_sheet["$S$25"].value, 110.0077271884082)
    assert_allclose(actual_test_sheet["$T$25"].value, 0.9053090770479797)
    assert_allclose(actual_test_sheet["$U$25"].value, 2711.7378946352073)
    assert_allclose(actual_test_sheet["$V$25"].value, 1.1896278235638376)
    assert_allclose(actual_test_sheet["$W$25"].value, 448.32977045252676)
    assert_allclose(actual_test_sheet["$X$25"].value, 0.09368112720240022)
    assert_allclose(actual_test_sheet["$Y$25"].value, 5004.60644493325)
    assert_allclose(actual_test_sheet["$Z$25"].value, 1.045741781752565)
    assert_allclose(actual_test_sheet["$AA$25"].value, 0.7801285169022669)
    assert actual_test_sheet["$B$26"].value == "Balance line and div. wall leakage"
    assert actual_test_sheet["$C$26"].value == "No"
    assert_allclose(actual_test_sheet["$F$26"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$26"].value, 1.578450967616677)
    assert_allclose(actual_test_sheet["$H$26"].value, 0.7185929389843275)
    assert_allclose(actual_test_sheet["$I$26"].value, 0.6527016569242936)
    assert_allclose(actual_test_sheet["$J$26"].value, -0.0038752260675583017)
    assert_allclose(actual_test_sheet["$K$26"].value, 1516369.3458798889)
    assert_allclose(actual_test_sheet["$L$26"].value, 0.1687418427433828)
    assert_allclose(actual_test_sheet["$M$26"].value, 0.037131561204681994)
    assert_allclose(actual_test_sheet["$N$26"].value, 1.4250828713353563)
    assert_allclose(actual_test_sheet["$O$26"].value, 94.08573706767193)
    assert_allclose(actual_test_sheet["$P$26"].value, 0.69043617133391)
    assert_allclose(actual_test_sheet["$Q$26"].value, 42.57668472606889)
    assert_allclose(actual_test_sheet["$R$26"].value, 0.3503850151099371)
    assert_allclose(actual_test_sheet["$S$26"].value, 77.2149669986991)
    assert_allclose(actual_test_sheet["$T$26"].value, 0.635440912147564)
    assert_allclose(actual_test_sheet["$U$26"].value, 3248.4539690898223)
    assert_allclose(actual_test_sheet["$V$26"].value, 1.4250828713353563)
    assert_allclose(actual_test_sheet["$W$26"].value, 589.4175986646264)
    assert_allclose(actual_test_sheet["$X$26"].value, 0.12316225393665012)
    assert_allclose(actual_test_sheet["$Y$26"].value, 5214.076803834693)
    assert_allclose(actual_test_sheet["$Z$26"].value, 1.08951183815005)
    assert_allclose(actual_test_sheet["$AA$26"].value, 0.6296018050922979)
    assert_allclose(actual_test_sheet["$F$27"].value, 6.0)
    assert actual_test_sheet["$B$28"].value == "Buffer Flow leakage"
    assert actual_test_sheet["$C$28"].value == "No"
    assert_allclose(actual_test_sheet["$F$28"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$29"].value, 8.0)
    assert actual_test_sheet["$B$30"].value == "Variable Speed"
    assert actual_test_sheet["$C$30"].value == "Yes"
    assert_allclose(actual_test_sheet["$F$30"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$31"].value, 10.0)
    assert actual_test_sheet["$F$32"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$32"].value, 2.1132889612096037)
    assert_allclose(actual_test_sheet["$H$32"].value, 0.9620789981532912)
    assert_allclose(actual_test_sheet["$I$32"].value, 0.6565768829918519)
    assert_allclose(actual_test_sheet["$K$32"].value, 8986326.812762942)
    assert_allclose(actual_test_sheet["$L$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$M$32"].value, 0.02605572065425804)
    assert_allclose(actual_test_sheet["$N$32"].value, 1.0)
    assert_allclose(actual_test_sheet["$O$32"].value, 132.99974938294014)
    assert_allclose(actual_test_sheet["$P$32"].value, 0.976001683297425)
    assert actual_test_sheet["$Q$32"].value == " - "
    assert actual_test_sheet["$R$32"].value == " - "
    assert_allclose(actual_test_sheet["$S$32"].value, 119.18470471381103)
    assert_allclose(actual_test_sheet["$T$32"].value, 0.9848421736969863)
    assert_allclose(actual_test_sheet["$U$32"].value, 2279.4842562705835)
    assert_allclose(actual_test_sheet["$V$32"].value, 1.0)
    assert actual_test_sheet["$W$32"].value == " - "
    assert actual_test_sheet["$X$32"].value == " - "
    assert_allclose(actual_test_sheet["$Y$32"].value, 4470.812747453942)
    assert_allclose(actual_test_sheet["$Z$32"].value, 0.9342024672365469)
    assert_allclose(actual_test_sheet["$AA$32"].value, 0.7953088677191706)
    assert actual_test_sheet["$F$34"].value == "SECTION 2 - Tested points - Results"
    assert actual_test_sheet["$G$35"].value == "Vol. Ratio"
    assert actual_test_sheet["$I$35"].value == "Mach"
    assert actual_test_sheet["$K$35"].value == "Reynolds"
    assert actual_test_sheet["$M$35"].value == "Flow Coef."
    assert actual_test_sheet["$O$35"].value == "Pd conv. (bar)"
    assert actual_test_sheet["$Q$35"].value == "Head (kJ/kg)"
    assert actual_test_sheet["$S$35"].value == "Head conv. (kJ/kg)"
    assert actual_test_sheet["$U$35"].value == "Flow conv. (m³/h)"
    assert actual_test_sheet["$W$35"].value == "Power (kW)"
    assert actual_test_sheet["$Y$35"].value == "Power conv. (KW)"
    assert actual_test_sheet["$AA$35"].value == "Polytropic Eff."
    assert actual_test_sheet["$AC$35"].value == "Mdiv"
    assert actual_test_sheet["$F$36"].value == "ERRO!"
    assert actual_test_sheet["$G$36"].value == "vi/vd"
    assert actual_test_sheet["$H$36"].value == "Rt/Rsp"
    assert actual_test_sheet["$I$36"].value == "Mt"
    assert actual_test_sheet["$J$36"].value == "Mt - Msp"
    assert actual_test_sheet["$K$36"].value == "Re_t"
    assert actual_test_sheet["$L$36"].value == "Re_t/Re_sp"
    assert actual_test_sheet["$M$36"].value == "ft"
    assert actual_test_sheet["$N$36"].value == "ft/fsp"
    assert actual_test_sheet["$O$36"].value == "Pdconv"
    assert actual_test_sheet["$P$36"].value == "Pdconv/Pdsp"
    assert actual_test_sheet["$Q$36"].value == "Ht"
    assert actual_test_sheet["$R$36"].value == "Ht/Hsp"
    assert actual_test_sheet["$S$36"].value == "Hconv"
    assert actual_test_sheet["$T$36"].value == "Hconv/Hsp"
    assert actual_test_sheet["$U$36"].value == "Qconv"

    assert actual_test_sheet["$V$36"].value == "Qconv/Qsp"
    assert actual_test_sheet["$W$36"].value == "Wt"
    assert actual_test_sheet["$X$36"].value == "Wt/Wsp"
    assert actual_test_sheet["$Y$36"].value == "Wconv"
    assert actual_test_sheet["$Z$36"].value == "Wconv/Wsp"
    assert actual_test_sheet["$AA$36"].value == "ht"
    assert actual_test_sheet["$AB$36"].value == "Reynolds corr."
    assert actual_test_sheet["$AC$36"].value == "kg/h"
    assert_allclose(actual_test_sheet["$F$37"].value, 1.0)
    assert_allclose(actual_test_sheet["$G$37"].value, 1.3227207253089355)
    assert_allclose(actual_test_sheet["$H$37"].value, 1.027364212958199)
    assert_allclose(actual_test_sheet["$I$37"].value, 0.4719605160746876)
    assert_allclose(actual_test_sheet["$J$37"].value, -0.06198613821683385)
    assert_allclose(actual_test_sheet["$K$37"].value, 1192374.3898159557)
    assert_allclose(actual_test_sheet["$L$37"].value, 0.1043429785471704)
    assert_allclose(actual_test_sheet["$M$37"].value, 0.008985131877381945)
    assert_allclose(actual_test_sheet["$N$37"].value, 0.7598590105162515)
    assert_allclose(actual_test_sheet["$O$37"].value, 254.9528884795821)
    assert_allclose(actual_test_sheet["$P$37"].value, 1.0180198390016855)
    assert_allclose(actual_test_sheet["$Q$37"].value, 23.729875113017336)
    assert_allclose(actual_test_sheet["$R$37"].value, 0.3849440362238192)
    assert_allclose(actual_test_sheet["$S$37"].value, 64.01433159458226)
    assert_allclose(actual_test_sheet["$T$37"].value, 1.0384350976491565)
    assert_allclose(actual_test_sheet["$U$37"].value, 529.6991851874122)
    assert_allclose(actual_test_sheet["$V$37"].value, 0.7598590105162514)
    assert_allclose(actual_test_sheet["$W$37"].value, 72.4141177108613)
    assert_allclose(actual_test_sheet["$X$37"].value, 0.025350645093947594)
    assert_allclose(actual_test_sheet["$Y$37"].value, 2271.9232190429843)
    assert_allclose(actual_test_sheet["$Z$37"].value, 0.7953520808832433)
    assert_allclose(actual_test_sheet["$AA$37"].value, 0.679970873305629)
    assert_allclose(actual_test_sheet["$F$38"].value, 2.0)
    assert_allclose(actual_test_sheet["$G$38"].value, 1.3192737459068735)
    assert_allclose(actual_test_sheet["$H$38"].value, 1.0246869257480393)
    assert_allclose(actual_test_sheet["$I$38"].value, 0.47506645243163736)
    assert_allclose(actual_test_sheet["$J$38"].value, -0.058880201859884074)
    assert_allclose(actual_test_sheet["$K$38"].value, 1194368.5372530876)
    assert_allclose(actual_test_sheet["$L$38"].value, 0.10451748353908377)
    assert_allclose(actual_test_sheet["$M$38"].value, 0.011184170506366536)
    assert_allclose(actual_test_sheet["$N$38"].value, 0.9458283807503725)
    assert_allclose(actual_test_sheet["$O$38"].value, 249.5994483430007)
    assert_allclose(actual_test_sheet["$P$38"].value, 0.9966437004591946)
    assert_allclose(actual_test_sheet["$Q$38"].value, 23.06263900998732)
    assert_allclose(actual_test_sheet["$R$38"].value, 0.3741201883362368)
    assert_allclose(actual_test_sheet["$S$38"].value, 61.38197687697352)
    assert_allclose(actual_test_sheet["$T$38"].value, 0.9957332610426396)
    assert_allclose(actual_test_sheet["$U$38"].value, 659.3387926928933)
    assert_allclose(actual_test_sheet["$V$38"].value, 0.9458283807503722)
    assert_allclose(actual_test_sheet["$W$38"].value, 84.84249462742811)
    assert_allclose(actual_test_sheet["$X$38"].value, 0.029701555969693018)
    assert_allclose(actual_test_sheet["$Y$38"].value, 2622.0135887465026)
    assert_allclose(actual_test_sheet["$Z$38"].value, 0.9179112861006485)
    assert_allclose(actual_test_sheet["$AA$38"].value, 0.7032212735002392)
    assert_allclose(actual_test_sheet["$F$39"].value, 3.0)
    assert_allclose(actual_test_sheet["$G$39"].value, 1.2866731198277017)
    assert_allclose(actual_test_sheet["$H$39"].value, 0.9993658463146237)
    assert_allclose(actual_test_sheet["$I$39"].value, 0.4730184033476288)
    assert_allclose(actual_test_sheet["$J$39"].value, -0.06092825094389265)
    assert_allclose(actual_test_sheet["$K$39"].value, 1205399.4462691715)
    assert_allclose(actual_test_sheet["$L$39"].value, 0.10548278262018757)
    assert_allclose(actual_test_sheet["$M$39"].value, 0.014395271717545245)
    assert_allclose(actual_test_sheet["$N$39"].value, 1.2173863525522004)
    assert_allclose(actual_test_sheet["$O$39"].value, 237.72924376650275)
    assert_allclose(actual_test_sheet["$P$39"].value, 0.9492463015752386)
    assert_allclose(actual_test_sheet["$Q$39"].value, 20.761393895089576)
    assert_allclose(actual_test_sheet["$R$39"].value, 0.336789583828203)
    assert_allclose(actual_test_sheet["$S$39"].value, 55.81019061334999)
    assert_allclose(actual_test_sheet["$T$39"].value, 0.905348213372536)
    assert_allclose(actual_test_sheet["$U$39"].value, 848.6423798107801)
    assert_allclose(actual_test_sheet["$V$39"].value, 1.2173863525522)
    assert_allclose(actual_test_sheet["$W$39"].value, 98.3947687725241)
    assert_allclose(actual_test_sheet["$X$39"].value, 0.03444591940224894)
    assert_allclose(actual_test_sheet["$Y$39"].value, 3043.630194905395)
    assert_allclose(actual_test_sheet["$Z$39"].value, 1.0655103080361963)
    assert_allclose(actual_test_sheet["$AA$39"].value, 0.7089633357315271)
    assert_allclose(actual_test_sheet["$F$40"].value, 4.0)
    assert_allclose(actual_test_sheet["$G$40"].value, 1.2056421414082092)
    assert_allclose(actual_test_sheet["$H$40"].value, 0.9364286549814107)
    assert_allclose(actual_test_sheet["$I$40"].value, 0.46779210993261205)
    assert_allclose(actual_test_sheet["$J$40"].value, -0.06615454435890938)
    assert_allclose(actual_test_sheet["$K$40"].value, 1198177.4782408962)
    assert_allclose(actual_test_sheet["$L$40"].value, 0.10485079852066409)
    assert_allclose(actual_test_sheet["$M$40"].value, 0.017686218956384073)
    assert_allclose(actual_test_sheet["$N$40"].value, 1.4956967821253158)
    assert_allclose(actual_test_sheet["$O$40"].value, 211.69613652892934)
    assert_allclose(actual_test_sheet["$P$40"].value, 0.8452968237059948)
    assert_allclose(actual_test_sheet["$Q$40"].value, 15.807602800854134)
    assert_allclose(actual_test_sheet["$R$40"].value, 0.2564296017658226)
    assert_allclose(actual_test_sheet["$S$40"].value, 43.44961011154344)
    assert_allclose(actual_test_sheet["$T$40"].value, 0.7048359171310478)
    assert_allclose(actual_test_sheet["$U$40"].value, 1042.653118294857)
    assert_allclose(actual_test_sheet["$V$40"].value, 1.4956967821253153)
    assert_allclose(actual_test_sheet["$W$40"].value, 98.17569085850735)
    assert_allclose(actual_test_sheet["$X$40"].value, 0.03436922487607469)
    assert_allclose(actual_test_sheet["$Y$40"].value, 3122.6834317089856)
    assert_allclose(actual_test_sheet["$Z$40"].value, 1.0931851677608913)
    assert_allclose(actual_test_sheet["$AA$40"].value, 0.6609600495811861)
    assert_allclose(actual_test_sheet["$F$41"].value, 5.0)
    assert_allclose(actual_test_sheet["$G$41"].value, 1.1250598933659246)
    assert_allclose(actual_test_sheet["$H$41"].value, 0.8738399949155996)
    assert_allclose(actual_test_sheet["$I$41"].value, 0.493933640164255)
    assert_allclose(actual_test_sheet["$J$41"].value, -0.04001301412726643)
    assert_allclose(actual_test_sheet["$K$41"].value, 1303631.450002704)
    assert_allclose(actual_test_sheet["$L$41"].value, 0.11407892486020633)
    assert_allclose(actual_test_sheet["$M$41"].value, 0.019465196266921888)
    assert_allclose(actual_test_sheet["$N$41"].value, 1.646142202110626)
    assert_allclose(actual_test_sheet["$O$41"].value, 185.47647380871248)
    assert_allclose(actual_test_sheet["$P$41"].value, 0.7406024349493391)
    assert_allclose(actual_test_sheet["$Q$41"].value, 12.411074754890574)
    assert_allclose(actual_test_sheet["$R$41"].value, 0.20133140976381822)
    assert_allclose(actual_test_sheet["$S$41"].value, 30.603247711510615)
    assert_allclose(actual_test_sheet["$T$41"].value, 0.4964433078353575)
    assert_allclose(actual_test_sheet["$U$41"].value, 1147.5289114071275)
    assert_allclose(actual_test_sheet["$V$41"].value, 1.6461422021106258)
    assert_allclose(actual_test_sheet["$W$41"].value, 127.48145197648562)
    assert_allclose(actual_test_sheet["$X$41"].value, 0.04462854961543344)
    assert_allclose(actual_test_sheet["$Y$41"].value, 3335.520691825507)
    assert_allclose(actual_test_sheet["$Z$41"].value, 1.1676949735079667)
    assert_allclose(actual_test_sheet["$AA$41"].value, 0.4796726454655151)
    assert_allclose(actual_test_sheet["$F$42"].value, 6.0)
    assert_allclose(actual_test_sheet["$F$43"].value, 7.0)
    assert_allclose(actual_test_sheet["$F$44"].value, 8.0)

    assert_allclose(actual_test_sheet["$F$45"].value, 9.0)
    assert_allclose(actual_test_sheet["$F$46"].value, 10.0)
    assert actual_test_sheet["$F$47"].value == "Guarantee"
    assert_allclose(actual_test_sheet["$G$47"].value, 1.3053209407746482)
    assert_allclose(actual_test_sheet["$H$47"].value, 1.0138497078917306)
    assert_allclose(actual_test_sheet["$I$47"].value, 0.5393468100631008)
    assert_allclose(actual_test_sheet["$J$47"].value, 0.0054001557715793735)
    assert_allclose(actual_test_sheet["$K$47"].value, 11335129.919783404)
    assert_allclose(actual_test_sheet["$L$47"].value, 0.9919210175521351)
    assert_allclose(actual_test_sheet["$M$47"].value, 0.012148632439350713)
    assert_allclose(actual_test_sheet["$N$47"].value, 1.0273914674227838)
    assert_allclose(actual_test_sheet["$O$47"].value, 246.03420399289672)
    assert_allclose(actual_test_sheet["$P$47"].value, 0.9824077782818108)
    assert actual_test_sheet["$Q$47"].value == " - "
    assert actual_test_sheet["$R$47"].value == " - "
    assert_allclose(actual_test_sheet["$S$47"].value, 59.71675323420715)
    assert_allclose(actual_test_sheet["$T$47"].value, 1.0094570422756588)
    assert_allclose(actual_test_sheet["$U$47"].value, 716.1965780896784)
    assert_allclose(actual_test_sheet["$V$47"].value, 1.0273914674227833)
    assert actual_test_sheet["$W$47"].value == " - "
    assert actual_test_sheet["$X$47"].value == " - "
    assert_allclose(actual_test_sheet["$Y$47"].value, 2763.0131257385583)
    assert_allclose(actual_test_sheet["$Z$47"].value, 0.967272230260304)
    assert_allclose(actual_test_sheet["$AA$47"].value, 0.7052172369023096)
