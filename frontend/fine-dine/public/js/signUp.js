// Global variables
BASE_URL = "https://admin-fine-dine.herokuapp.com/api/v1/admin"

function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

function setCookie(name,value,days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days*24*60*60*1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/";
}

$(document).ready(function() {
    if(getCookie("jwt_token")!=null)
        window.location = "RestroSelection.html";
    $('#loading_icon').fadeOut(200)
});

function _create_admin(f_name, l_name, email, phone, password,callback){
 obj = {
    f_name:f_name,
    l_name:l_name,
    email_id:email,
    contact:phone,
    password:password
}
 $.ajax({
     type: "POST",
     url: BASE_URL+"/create_admin",
     data: JSON.stringify(obj),
     dataType: "json",
     processData: false,
     contentType: "application/json",
     success: function (response) {
        if(response.hasOwnProperty("error")){
            alert(response.error)
        }else if(response.hasOwnProperty("jwt_token")){
            setCookie("jwt_token", response.jwt_token, 30)
            window.location = "RestroSelection.html";
        }else{
            alert('Unknown response')
            console.log(response)
        }
     },
     statusCode: {
        401: function(xhr) {
            var obj = JSON.parse(xhr.responseText)
            alert(obj.error)
        }
    },
    failure: function(response){
        alert(response)
    },
    complete: function () {  
        callback()
    }
 });  
}

function createAdmin(e){
    e.preventDefault();

    fname = document.getElementById("fname").value;
    lname = document.getElementById("lname").value;
    email = document.getElementById("email").value;
    phone = document.getElementById("phone").value;
    pass = document.getElementById("pass").value;

    $('#loading_icon').fadeIn(200)
    _create_admin(fname, lname, email, phone, pass,function(){
        $('#loading_icon').fadeOut(200)
    })
}