$(document).ready(function() {
    showTopQuestions();
});

function showTopQuestions() {
    $.ajax({
        type: 'POST',
        url: "http://130.245.170.46/questions/top",
        dataType: 'json',
        crossDomain: true,
        success: function(json) {
            $('#topQuestions').text("");
            //console.log(json);
            questions = json['questions'];
            for (var i=0; i<questions.length; i++) {
                $('#topQuestions').append('<a href="/questions/' + questions[i]['id'] + '/view">' + questions[i]['title'] + '</a> ' + questions[i]['view_count'] + ' views <br><br>');
            }
        },
        error: function(data) {
            alert("There was an error fetching the top questions.");
            console.log(data);
        }
    });
}

function ask() {
    var title = $("#title").val();
    var body = $("#body").val();
    var tags = $("#tags").val().split(" ");
    $.ajax({
        type: 'POST',
        url: "http://130.245.170.46/questions/add",
        dataType: 'json',
        data: JSON.stringify({'title':title, 'body':body, 'tags':tags}),
        crossDomain: true,
        success: function(json) {
            if (json['status'] == 'OK') {
                $("#output").text("");
                $("#output").append('<span style="color: green;">Your question has been submitted!</span>');
                showTopQuestions();
            }
            else {
                $("#output").text("");
                $("#output").append('<span style="color: red;">ERROR: ' + json['error'] + '</span>');
	        }
        },
        error: function(data) {
            alert("There was an error.");
            console.log(data);
        }
    });
}

function answer() {
    var body = $("#abody").val();
    var id =$("#qID").data('content');
    console.log(id);
    console.log(body);
    $.ajax({
        type: 'POST',
        url: "http://130.245.170.46/questions/" + id + "/answers/add",
        dataType: 'json',
        data: JSON.stringify({'body':body}),
        crossDomain: true,
        success: function(json) {
            if (json['status'] == 'OK') {
                $("#output").text("");
                $("#output").append('<span style="color: green;">Your answer has been submitted!</span>');
                showAnswers();
            }
            else {
                $("#output").text("");
                $("#output").append('<span style="color: red;">ERROR: ' + json['error'] + '</span>');
            }
        },
        error: function(data) {
            alert("There was an error.");
            console.log(data);
        }
    });
}
