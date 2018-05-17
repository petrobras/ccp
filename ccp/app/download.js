var data = source.data;
var filetext = 'flow(m**3/s),head(J/kg),efficiency(%),speed(RPM)\n';

for (var i = 0; i < data['flow_v'].length; i++) {
    var currRow = [data['flow_v'][i].toString(),
                   data['head'][i].toString(),
                   (100*data['eff'][i]).toString(),
                   data['speed'][i].toString().concat('\n'),];

    var joined = currRow.join();
    filetext = filetext.concat(joined);
}

var filename = 'curves.csv';
var blob = new Blob([filetext], { type: 'text/csv;charset=utf-8;' });

if (navigator.msSaveBlob) {
    navigator.msSaveBlob(blob, filename);
} else {
    var link = document.createElement("a");
    link = document.createElement('a')
    link.href = URL.createObjectURL(blob);
    link.download = filename
    link.target = "_blank";
    link.style.visibility = 'hidden';
    link.dispatchEvent(new MouseEvent('click'))
}