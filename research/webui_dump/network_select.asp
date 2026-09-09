<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>
    <link rel="stylesheet" href="res/css/main.css">
</head> 
<body> 
<div class="wrap">
<form>	    
    <input type="hidden" name="goformId" value="NET_SELECT_NEW">  
    <input type="hidden" name="lucknum_NET_SELECT_NEW" value="">  
    <input type="hidden" name="net_select" value="Automatic">
    <input type="hidden" name="net_select_mdoe" value="Automatic">
        
	<table><tr><th id="ui_network_select">Network Select</th></tr>
		<tr><td>
			<div id="net_droplist1" style="display:none;">
				<p></p>
				<ul id="ui_wcdma">
					<li value="Automatic" id="ui_automatic">Automatic</li>
					<li value="Only_GSM_EDGE">Only GSM/EDGE</li>
					<li value="Only_UMTS">Only UMTS</li>
					<li value="Only_4G">Only 4G</li>
					<li value="Only_EVDO">Only EVDO</li>
				</ul>
			</div>
			<div id="net_droplist2" style="display:none;">
				<p></p>
                <ul id="ui_cdma">
                    <li value="Automatic" id="ui_automatic">Automatic</li>
					<li value="Only_GSM_EDGE">Only GSM/EDGE</li>
					<li value="Only_UMTS">Only UMTS</li>
					<li value="Only_4G">Only 4G</li>
					<li value="Only_EVDO">Only EVDO</li>
				</ul>
			</div>
		</td></tr>
		<tr><td>
		<input type="button" class="btn" onclick="apply();" value="Apply"  id="btn_apply"> 
		<input type="button" class="btn" onclick="location.reload();" value="Reset" id="btn_reset">
     </td></tr>
	</table>
</form>
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';

if ('ok' != 'ok') {
	top.location.href = 'login.asp';
}

var ppp_status = 'ppp_connected';
var dual_mode_type = 'WCDMA';

function apply() {
	$('input[name=net_select]').val($('input[name=AutoSelect]').val());
	$.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r) {
		parent.loading(1000,1);
	});
}

function disconnect() {
	$.get('/goform/goform_process?goformId=NET_CONNECT&lucknum_NET_CONNECT=&dial_mode=auto_dial&action=disconnect&wan_conn_which_page=wan_operation',function(r){
		parent.loading(2000,1);
	});
}

$(function() {
	$.i18n(lang,'network_select',function(){
        if(dual_mode_type == 'CDMA') {
            $('#net_droplist2').show().droplist('AutoSelect','Automatic');
        } else {
            $('#net_droplist1').show().droplist('AutoSelect','Automatic'); 
        }
		parent.setHeight(300);
	});
	
	parent.setHeight(300);
});
</script>
</body>
</html>