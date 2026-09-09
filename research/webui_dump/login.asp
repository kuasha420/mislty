<!DOCTYPE html>
<html> 
<head> 
    <meta charset="utf-8"> 
    <title>4G Router</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">  
    <link rel="shortcut icon" href="favicon.ico">  
    <link rel="stylesheet" href="res/css/login.css">
</head>
<body> 
<div class="wrap">
	<div class="logo"></div>
	<div class="main">
		<form onsubmit="login();return false;">
			<input type="hidden" value="LOGIN_NEW" name="goformId" id="goformId">
			<input type="hidden" value="" name="lucknum" id="lucknum">
			<input type="hidden" value="" name="systemDate" id="systemDate">
			<input type="hidden" value=""  name="save_login" id="save_login">
			<div class="login">
				<div id="ui_login_title">Administrator Login</div>
				<table id="login_input">
					<tr>
						<td width="90" id="ui_username">Username</td>
						<td><input type="text" id="username" name="user"></td>
					</tr>
					<tr>
						<td id="ui_password">Password</td>
						<td><input type="password" id="password" name="psw"></td>
					</tr>
					<tr>
						<td id="ui_language">Language</td>
						<td>						
							<div id="language_droplist">
								<p></p>
								<ul>
									<li value="en">English</li>
									<li value="cn">简体中文</li>
									<li value="tw">繁體中文</li>
								</ul>
							</div>
						</td>
					</tr>
				</table>
				<div style="text-align:center;">
						<input class="btn" type="submit" id="btn_login" value="Login">
						<input class="btn" type="reset" id="btn_cancel" value="Cancel">
				</div>
			</div>
		</form>
	</div>
	<div id="ui_copyright">&copy; 2014 QUALCOMM</div>
</div>
<script src="res/js/jquery.js"></script>
<script>
var lang = 'en';
var login_error = 'ok';
var login_save =  '';
var psw_save   = ''; 

function writeLucknum() {
	var time = new Date().getTime(), lucknum = time + Math.floor(Math.random() * 1000000);
	$('#systemDate').val(time);
	document.cookie = 'lucknum=' + lucknum;
	$('#lucknum').val(lucknum);
} 

function login() {
	writeLucknum();
	$.post('/goform/goform_process',$('form:eq(0)').serialize(),function(r){
		if(r.indexOf('login.asp') > -1 ){
			alert(text['tip_login_error']);
		} else {
			top.location.href ='home.asp';
		}
	});
}

$(function() {
	$('#language_droplist').droplist('language',lang,function(v) {
		$.get('/goform/goform_process?goformId=SET_LANGUAGE&language='+v,function(r){
			location.href ='login.asp';
		});
	});
	$.i18n(lang,'login');
});
</script>
</body>
</html>