$(document).ready(function() {
    showGame()
    $(".ttt").click(function(event) {
    	var c = $("#"+event.target.id).text()
    	if (c != ' ')
    		return;
    	var index = event.target.id;
        $("#"+index).text("X");
        $.ajax({
            type: 'POST',
            url: "http://130.245.170.46/ttt/play",
            data: JSON.stringify({'move': index}),
            dataType: 'json',
            crossDomain: true,
            success: function(json) {
                console.log(json)
                var grid = json['grid']
                for (i=0; i<9; i++) {
                    $("#" + i.toString()).text(grid[i].toString());
                }
                var winner = json['winner']
                if (winner != ' ' || noMoveLeft(grid)) {
                    if (winner == ' ')
                        $("#winner").text("It's a tie!");
                    else if (winner == 'X')
                        $("#winner").text("You win!");
                    else if (winner == 'O')
                        $("#winner").text("You lose!");
                    showScore();
                    $("#status2").text("Click here to play again");
                }
            },
            error: function(data) {
                alert("ERROR!");
                console.log(data);
            }
        });
    });
    $("#status2").click(function() {
        resetGame()
        $("#status2").text("")
	$("#winner").text("")
    })
});

function showGame() {
    showScore();
    grid = $.cookie('cse356game');
    console.log('current game state: ' + grid);
    for (i=0; i<9; i++)
	    $("#" + i.toString()).text(grid[i].toString());
    if ($.cookie('cse356gameover') == 'true')
        $("#status2").text("Click here to play again")
}

function resetGame() {
    for (i=0; i<9; i++)
        $("#" + i.toString()).text(' ');
}

function noMoveLeft(game) {
    for (var i=0; i<game.length; i++)
        if (game[i] == " ")
            return false
    return true
}

function showScore() {
    $.ajax({
        type: 'POST',
        url: "http://130.245.170.46/getscore",
        dataType: 'json',
        crossDomain: true,
        success: function(json) {
            console.log(json)
            if (json['status'] == 'OK') {
                var score = "Wins: " + json['human'] + "  Losses: " + json['wopr'] + " Ties: " + json['tie'];
                $("#score").text(score);
            }
        },
        error: function(data) {
            alert("ERROR!");
            console.log(data);
        }
    });
}
