$(document).ready(function() {
    showTopQuestions();
});

function showTopQuestions() {
    $.ajax({
        type: 'POST',
        url: "http://130.245.170.46/topQuestions",
        dataType: 'json',
        crossDomain: true,
        success: function(json) {
            console.log(json)
            questions = json['questions']
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
    var tags = [];
    tags.push($("#tags").val());
    $.ajax({
        type: 'POST',
        url: "http://130.245.170.46/questions/add",
        dataType: 'json',
        data: JSON.stringify({'title':title, 'body':body, 'tags':tags}),
        crossDomain: true,
        success: function(json) {
            if (json['status'] == 'OK')
                alert("Your question has been submitted!");
            else
                alert("ERROR: " + json['error']);
        },
        error: function(data) {
            alert("There was an error.");
            console.log(data);
        }
    });
}
