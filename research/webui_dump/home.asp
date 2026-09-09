<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>   
    <base target="mainifr">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="shortcut icon" href="favicon.ico">
    <link rel="stylesheet" href="res/css/home.css">
    <link rel="stylesheet" href="res/css/jquery.popup.css">
    <script src="res/js/jquery.js"></script>
    <script src="res/js/jquery.popup.js"></script>
    <script>
	var lang = 'en';
	
	if ('ok' != 'ok') {
		top.location.href = 'login.asp';
	}
	
	var network_type = 'LTE';
	var sim_status = 'modem_init_complete';
	var signal_strength = '5'; //
	
	var wifi_status = '1';
	var roam_status	= 'roam_off';
	
	var sms_unread_count = '';
	var new_message = '';
	
	var  sd_card_state = '0'; //0, 1, 2
	var  sd_card_option = '0';
	
	$(function(){
		$('.menu li.sub').mouseenter(function(){
			$(this).find('ul').slideDown('fast');
		}).mouseleave(function(){
			$(this).find('ul').slideUp('fast');
		});


        var isMobile = {
            Android: function() {
                return navigator.userAgent.match(/Android/i) ? true : false;
            },
            BlackBerry: function() {
                return navigator.userAgent.match(/BlackBerry/i) ? true : false;
            },
            iOS: function() {
                return navigator.userAgent.match(/iPhone|iPad|iPod/i) ? true : false;
            },
            Windows: function() {
                return navigator.userAgent.match(/IEMobile/i) ? true : false;
            },
            any: function() {
                return (isMobile.Android() || isMobile.BlackBerry() || isMobile.iOS() || isMobile.Windows());
            }
        };
		
		if( isMobile.any() ) {
             $('.menu li.sub ul a').click(function(){
                $(this).parent().parent().slideUp('fast');
            });                                             
        }
		
		if(sim_status == 'modem_init_complete') {                                                                           
			$('#logo_sim')[0].src='res/img/sim_yes.gif'; 
		} else {                                                                           
			$('#logo_sim')[0].src='res/img/sim_no.gif';
		}
		
		if (network_type.isEmpty()  || network_type.toLowerCase() == 'no service'   ||  sim_status == 'modem_sim_undetected' ) {
			$('#logo_signal')[0].src='res/img/signal_0.gif';
		} else {
			$('#logo_signal')[0].src='res/img/signal_'+signal_strength+'.gif';
		}   
		
		if(wifi_status == '0') {                                                                           
			$('#logo_wifi')[0].src='res/img/wifi_no.gif'; 
		} else {                                                                           
			$('#logo_wifi')[0].src='res/img/wifi_yes.gif';
		}
		
		if(roam_status.toLowerCase() == 'roam_on') {                                                                           
			$('#logo_roaming')[0].src='res/img/roaming_yes.gif';
		} else {                                                                            
			$('#logo_roaming')[0].src='res/img/roaming_no.gif';
		}
		
		$.i18n(lang,'home');
	});

	function setHeight(h){
		if (top.location != self.location)top.location=self.location;
		try{
			var m = $('#mainifr'),md=m[0].contentWindow.document;
			if(h) {
				m.attr('height',h);
			}else {
				m.attr('height',jQuery.browser.msie ? Math.max(md.documentElement.scrollHeight, md.body.scrollHeight) : Math.max(md.documentElement.offsetHeight,md .body.offsetHeight));
			}
		}catch(e){}
	}
	
	function loading(timeout,refresh) {
		var ol = $('.overlay'),box = $('.box');
		
		if(!-[1,]&&!window.XMLHttpRequest) { //ie6
			ol.css({position:'absolute',width: Math.max($(window).width(),$(document.body).width()),height: Math.max($(window).height(),$(document.body).height())});
		}
		
		ol.show();
		box.show().css({left:(($(document).width())/2 - 36)+'px',top:($(document).scrollTop()+210)+'px'});
		
		setTimeout(function(){
			ol.hide();
			box.hide();
			if(refresh == 1){
				top.frames['mainifr'].location.reload();
			}
		}, timeout);
	}

	function logout() {
		if(confirm(text['tip_logout_confirm'])) {
			$.get('/goform/goform_process?goformId=LOGOUT',function(r) {
				top.location.href ='login.asp';
			});
		}
	}
	
	
	function win(title,url,width,height,callback){
		$(document.body).popup({
			buttons: {
				Apply: function(){
					if(callback){
						callback.apply(this, arguments);
					}else{
						$('#popup_iframe')[0].contentWindow.apply();   
					}
				},
				Cancel: function(){
					$(document.body).popup({close:true});
				}                              
			},
			title:title,
			url:url,
			width:width,
			height:height
		});
	}

	function tip(type,text,callback){	
		$(document.body).popup({
			splash:true,
			type:type,
			title:type==-1?'Warning':(type==2?'Confirm':'Tips'),
			text:text
		},callback);
	}
	
    </script>
	<!--[if lte IE 6]>
	<style>@media screen{* html{overflow-y: hidden;}* html body{height:100%;overflow:auto;}}</style>
	<script src="res/js/DD_belatedPNG.js"></script>
	<script>
		if((window.navigator.appName.toUpperCase().indexOf("MICROSOFT")>=0)&&(document.execCommand)) {
			try{
				document.execCommand("BackgroundImageCache", false, true);
			} catch(e){}
		}
		DD_belatedPNG.fix('.sub img, img');
	</script>
	<![endif]-->
</head> 
<body> 
<div class="wrap">
	<div class="header">
		<div class="logout"><a href="javascript:;" onclick="logout();" target="_self" id="ui_logout">Logout</a></div>
		<div class="status">
			<img src="res/img/wifi_yes.gif" 	id="logo_wifi"		title="Wi-Fi">
			<img src="res/img/roaming_yes.gif" 	id="logo_roaming"	title="Roaming">
			<img src="res/img/signal_3.gif" 	id="logo_signal"	title="Signal">
			<img src="res/img/sim_yes.gif" 		id="logo_sim"		title="SIM">
		</div>
	</div>
	<div class="menu">
		<li class="sub"><a class="item" href="network_connect.asp"><img src="res/img/home.png"><div id="ui_home">Home</div></a>
			<ul>
				<li><a href="network_connect.asp"	id="ui_network_connect">Network Connect</a></li>
				<li><a href="reset_factory.asp" 	id="ui_reset_factory">Reset Factory</a></li>
				<li><a href="dhcp_setting.asp" 		id="ui_dhcp_setting">DHCP Settings</a></li>
				<li><a href="update_password.asp" 	id="ui_update_password">Update Password</a></li>
			</ul>
		</li>
		
		<li class="sub"><a class="item" href="connection_mode.asp"><img src="res/img/ggg.png"><div id="ui_3g_setting">4G Settings</div></a>
			<ul>
				<li><a href="connection_mode.asp"	id="ui_connection_mode">Connection Mode</a></li>
				<li><a href="network_select.asp"	id="ui_network_selection">Network Selection</a></li>
				<li><a href="apn_setting.asp"	    id="ui_apn_setting">APN Settings</a></li>
			</ul>
		</li>
		
		<li class="sub"><a class="item" href="wifi_profile.asp"><img src="res/img/user.png"><div id="ui_wifi_setting">Wi-Fi Settings</div></a>
			<ul>
				<li><a href="wifi_profile.asp"		id="ui_wifi_profile">Wi-Fi Profiles</a></li>
				<li><a href="wifi_security.asp"		id="ui_wifi_security">Wi-Fi Security</a></li>
				<li><a href="wifi_standby.asp"		id="ui_wifi_standby">Wi-Fi Standby</a></li>
				<li><a href="station_list.asp"		id="ui_station_list">Station List</a></li>
			</ul>
		</li>
		
		<li class="sub"><a class="item" href="basic_status.asp"><img src="res/img/wifi.png"><div id="ui_status">Status</div></a>
			<ul>
				<li><a href="data_statistics.asp" 	id="ui_data_statistics">Data Statistics</a></li>
				<li><a href="basic_status.asp"		id="ui_basic_status">Basic Status</a></li>
				<li><a href="network_status.asp"	id="ui_network_status">Network Status</a></li>
			</ul>
		</li>
		<li class="sub"><a class="item" href="help_en.html"><img src="res/img/nas.png"><div id="ui_help_information">Help Information</div></a></li>
		<div class="clear"></div>
	</div>
	<div style="padding:20px;">
		<iframe src="network_connect.asp" name="mainifr" id="mainifr" frameborder="0" scrolling="no" width="100%" height="400" marginwidth="0" marginheight="0"></iframe>
	</div>
	<div id="ui_copyright">&copy; 2014 QUALCOMM</div>
	
	<div class="overlay"></div>
	<div class="box"><img border="0" src="res/img/waiting.gif" width="75" height="75"></div>
</div>
</body>
</html>