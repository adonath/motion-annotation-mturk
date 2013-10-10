var canvas_first;
var canvas_second;
var ctx_first;
var ctx_second;
var ctx_first_cutout;
var ctx_second_cutout;
var ctx_diff;
var base_url;
var image_first_path;
var image_second_path;
var image_first;
var image_second;
var fi_height;
var fi_width;
var si_height;
var si_width;
var c; // correspondences
var c_temp;
var first_idata;
var second_idata;
var diff_idata;
var error;
var errors;
var begin_time;

// Array Remove - By John Resig (MIT Licensed)
Array.prototype.remove = function(from, to) {
  var rest = this.slice((to || from) + 1 || this.length);
  this.length = from < 0 ? this.length + from : from;
  return this.push.apply(this, rest);
};

$(function() {
  $(".alert").alert()
  initialize();
  canvas_first.bind('mouseenter', enter_canvas);
  canvas_second.bind('mouseenter', enter_canvas);
  canvas_first.bind('mousemove', canvas_first_mousemove);
  canvas_first.bind('click', canvas_first_mouseclick);
  $('.control').on("mouseover", 'tr.value', function() {highlight_correspondence(parseInt($(this).attr('id'))) });
  $('.control').on("click", 'a.removec', function() {
    remove_correspondence(parseInt($(this).closest("tr").attr('id'))) });
  $('.control').bind('mouseleave', function() {
    ctx_first.drawImage(image_first,0,0,fi_width,fi_height,0,0,canvas_first.width(),canvas_first.height());
    ctx_second.drawImage(image_second,0,0,si_width,si_height,0,0,canvas_second.width(),canvas_second.height());
  });
  document.getElementById('assignmentId').value = get_url_param('assignmentId');
  // Check if the worker is PREVIEWING the HIT or if they've ACCEPTED the HIT
  if (get_url_param('assignmentId') == "ASSIGNMENT_ID_NOT_AVAILABLE") {
  // If we're previewing, disable the button and give it a helpful message
  document.getElementById('submitButton').disabled = true;
  document.getElementById('submitButton').value = "You must ACCEPT the HIT before you can submit the results.";
  }
  else {
    var form = document.getElementById('mturk_form');
    if (document.referrer && ( document.referrer.indexOf('workersandbox') != -1) ) {
      form.action = "http://workersandbox.mturk.com/mturk/externalSubmit";
    }
  }
})

function initialize() {
  c=[];
  c_temp=[];
  errors=[];
  begin_time = new Date();
  canvas_first = $("#canvas_first");
  canvas_first.get()[0].width = canvas_first.get()[0].height = canvas_first.parent().width();
  canvas_second = $("#canvas_second");
  canvas_second.get()[0].width = canvas_second.get()[0].height = canvas_second.parent().width();
  canvas_first_cutout = $("#canvas_first_cutout");
  canvas_first_cutout.get()[0].width = canvas_first_cutout.get()[0].height = canvas_first_cutout.parent().width();
  canvas_second_cutout = $("#canvas_second_cutout");
  canvas_second_cutout.get()[0].width = canvas_second_cutout.get()[0].height = canvas_second_cutout.parent().width();
  canvas_diff = $("#canvas_diff");
  canvas_diff.get()[0].width = canvas_diff.get()[0].height = canvas_diff.parent().width();
  ctx_first = document.getElementById("canvas_first").getContext('2d');
  ctx_second = document.getElementById("canvas_second").getContext('2d');
  ctx_first_cutout = document.getElementById("canvas_first_cutout").getContext('2d');
  ctx_second_cutout = document.getElementById("canvas_second_cutout").getContext('2d');
  ctx_diff = document.getElementById("canvas_diff").getContext('2d');
  ctx_first.strokeStyle = 'red';
  ctx_second.strokeStyle = 'red';
  base_url = "../MTurkTemp/";
  //image_first_path = base_url + "first_0_0_frame10.png";
  //image_second_path = base_url + "second_0_0_frame10.png";
  image_first_path = base_url + "first_" + get_url_param('images');
  image_second_path = base_url + "second_" + get_url_param('images')
  image_first = new Image();
  image_second = new Image();
  image_first.crossOrigin='';
  image_second.crossOrigin='';
  image_first.src=image_first_path;
  image_second.src=image_second_path;
  fi_height=image_first.height-1;
  si_height=image_second.height-1;
  fi_width=image_first.width-1;
  si_width=image_second.width-1;
  ctx_first.drawImage(image_first,0,0,fi_width,fi_height,0,0,canvas_first.width(),canvas_first.height());
  ctx_second.drawImage(image_second,0,0,si_width,si_height,0,0,canvas_second.width(), canvas_second.height());
};

function location_in_elem(x,y, elem) {
  return [x-elem.left, y-elem.top];
}

function enter_canvas(event) {
  $(this).css({cursor: 'none'});
}

function canvas_first_mousemove(event) {
  if (c.length%4==0) {
    loc = location_in_elem(event.pageX, event.pageY, {top: this.offsetTop, left: this.offsetLeft});
    ctx_first.drawImage(image_first,0,0,fi_width,fi_height,0,0,canvas_first.width(),canvas_first.height());
    x=loc[0]-12;
    y=loc[1]-12;
    ctx_first.strokeRect(x, y, 24, 24);
    ctx_first.beginPath();
    ctx_first.arc(loc[0],loc[1],3,0,Math.PI*2,false);
    ctx_first.closePath();
    ctx_first.stroke();
  }
}

function canvas_second_mousemove(event) {
  if (c.length%4==2) {
    loc = location_in_elem(event.pageX, event.pageY, {top: this.offsetTop, left: this.offsetLeft});
    ctx_second.drawImage(image_second,0,0,fi_width,fi_height,0,0,canvas_first.width(),canvas_first.height())
    error=compute_error(loc[0], loc[1]);
    $('.error').html(error.toFixed(2));
    x=loc[0]-12;
    y=loc[1]-12;
    ctx_second.strokeRect(x, y, 24, 24);
  }
}

function compute_error(px,py) {
  x=px-10;
  y=py-10;
  if (x<0)
    x=0;
  if (y<0)
    y=0;
  lx=c[c.length-2]-10;
  ly=c[c.length-1]-10;
  if (lx<0)
    lx=0;
  if (ly<0)
    ly=0;

  first_idata = ctx_first.getImageData(lx, ly, 20, 20);
  var temp_first_idata = $("<canvas>")
    .attr("width", first_idata.width)
    .attr("height", first_idata.height)[0];
  temp_first_idata.getContext('2d').putImageData(first_idata,0,0);
  ctx_first_cutout.drawImage(temp_first_idata,0,0,first_idata.width,first_idata.height,0,0,canvas_first_cutout.width(),canvas_first_cutout.height());

  second_idata = ctx_second.getImageData(x, y, 20, 20);
  var temp_second_idata = $("<canvas>")
    .attr("width", second_idata.width)
    .attr("height", second_idata.height)[0];
  temp_second_idata.getContext('2d').putImageData(second_idata,0,0);
  ctx_second_cutout.drawImage(temp_second_idata,0,0,second_idata.width,second_idata.height,0,0,canvas_second_cutout.width(),canvas_second_cutout.height());

  calc_diff_image();

  e= 0;
  for (i=0;i<first_idata.data.length;i++) {
    e+=Math.pow(Math.abs(first_idata.data[i]-second_idata.data[i]), 2);
  }
  e=Math.sqrt(e/400);
  return e;
}

function calc_diff_image() {
  var temp_diff_idata = $("<canvas>")
    .attr("width", 20)
    .attr("height", 20)[0];
  diff_idata = temp_diff_idata.getContext('2d').createImageData(20,20);
  d=diff_idata.data;
  len=d.length;
  for (i=0;i<len;i++) {
    if (i%4==3)
      d[i]=255;
    else
      d[i]=Math.abs(first_idata.data[i]-second_idata.data[i]);
  }
  temp_diff_idata.getContext('2d').putImageData(diff_idata,0,0);
  ctx_diff.drawImage(temp_diff_idata,0,0,diff_idata.width,diff_idata.height,0,0,canvas_diff.width(),canvas_diff.height());
}

function draw_correspondences(event, loc) {
  ctx_first.drawImage(image_first,0,0,fi_width,fi_height,0,0,canvas_first.width(),canvas_first.height())
  ctx_second.drawImage(image_second,0,0,si_width,si_height,0,0,canvas_second.width(),canvas_second.height())
  for (i=0;i<c.length;i+=4) {
    ctx_first.beginPath();
    ctx_second.beginPath();
    ctx_first.moveTo(c[i], c[i+1]);
    ctx_second.moveTo(c[i], c[i+1]);
    ctx_first.lineTo(c[i+2], c[i+3]);
    ctx_second.lineTo(c[i+2], c[i+3]);
    ctx_first.closePath();
    ctx_second.closePath();
    ctx_first.stroke();
    ctx_second.stroke();
  }
  if (c.length%4!=0) {
    ctx_first.strokeStyle = 'red';
    ctx_second.strokeStyle = 'red';
    ctx_first.beginPath();
    ctx_second.beginPath();
    ctx_first.moveTo(c[c.length-2], c[c.length-1]);
    ctx_second.moveTo(c[c.length-2], c[c.length-1]);
    ctx_first.lineTo(loc[0], loc[1]);
    ctx_second.lineTo(loc[0], loc[1]);
    ctx_first.closePath();
    ctx_second.closePath();
    ctx_first.stroke();
    ctx_second.stroke();
    ctx_first.strokeStyle = 'blue';
    ctx_second.strokeStyle = 'blue';
  }
}

function deliver_message(text) {
  $(".messages").html("<div class='alert alert-success'><a class='close' data-dismiss='alert'>&times;</a> "+"<p>"+text+"</p></div>");
}

function canvas_first_mouseclick(event) {
  if (c.length/4 == 8){
		deliver_message("You've found eight correspondences! Please submit your results!");
		}
  else{
	  canvas_second.unbind('click').bind('click', canvas_second_mouseclick);
	  canvas_first.unbind('click');
	  canvas_first.unbind('move');
	  $('.c1').removeClass('active');
	  $('.c2').addClass('active');
	  ctx_first.drawImage(image_first,0,0,fi_width,fi_height,0,0,canvas_first.width(),canvas_first.height());
	  ctx_second.drawImage(image_second,0,0,si_width,si_height,0,0,canvas_second.width(),canvas_second.height());
	  loc = location_in_elem(event.pageX, event.pageY, {top: this.offsetTop, left: this.offsetLeft});
	  c.push(loc[0], loc[1]);
	  deliver_message("Now go ahead and use your mouse to identify the same Area in the second Frame.");
	  x=loc[0]-12;
	  y=loc[1]-12;
	  ctx_first.strokeRect(x, y, 24, 24);
	  lx=c[c.length-2]-10;
	  ly=c[c.length-1]-10;
	  if (lx<0)
		lx=0;
	  if (ly<0)
	  ly=0;
	  first_idata = ctx_first.getImageData(lx, ly, 20, 20);
	  var temp_first_idata = $("<canvas>")
		.attr("width", first_idata.width)
		.attr("height", first_idata.height)[0];
	  temp_first_idata.getContext('2d').putImageData(first_idata,0,0);
	  ctx_first_cutout.drawImage(temp_first_idata,0,0,first_idata.width,first_idata.height,0,0,canvas_first_cutout.width(),canvas_first_cutout.height());
	  canvas_second.bind('mousemove', canvas_second_mousemove);
  }
}

function canvas_second_mouseclick(event) {
  c_temp.push(loc[0], loc[1]);
  $('.c2').removeClass('active');
  $('.c3').addClass('active');
  deliver_message("Sum of squared errors was: " + error.toFixed(2) + ". You may now use the a,w,s,d keys to improve the result. Try to minimize the sum of squared errors shown to the right. The difference Picture with in the green bordered area may be useful! Press enter when done.");
  canvas_second.unbind('click');
  $('body').unbind('keypress').bind('keypress', canvas_second_keypress);
  canvas_second.unbind('mousemove');
}

function canvas_second_keypress(event) {
  if (event.which == 97) {
    // left
    c_temp[0]-=1;
    ctx_second.drawImage(image_second,0,0,si_width,si_height,0,0,canvas_second.width(),canvas_second.height())
    error=compute_error(c_temp[0], c_temp[1]);
    x=c_temp[0]-12;
    y=c_temp[1]-12;
    ctx_second.strokeRect(x, y, 24, 24);
    $('.error').html("<a class='close' data-dismiss='alert'>&times;</a> Sum of squared errors: "+ error.toFixed(2));
  }
  else if (event.which == 100) {
    // right
    c_temp[0]+=1;
    ctx_second.drawImage(image_second,0,0,si_width,si_height,0,0,canvas_second.width(),canvas_second.height())
    error=compute_error(c_temp[0], c_temp[1]);
    x=c_temp[0]-12;
    y=c_temp[1]-12;
    ctx_second.strokeRect(x, y, 24, 24);
    $('.error').html("<a class='close' data-dismiss='alert'>&times;</a> Sum of squared errors: "+ error.toFixed(2));
  }
  else if (event.which == 119) {
    // up
    c_temp[1]-=1;
    ctx_second.drawImage(image_second,0,0,si_width,si_height,0,0,canvas_second.width(),canvas_second.height())
    error=compute_error(c_temp[0], c_temp[1]);
    x=c_temp[0]-12;
    y=c_temp[1]-12;
    ctx_second.strokeRect(x, y, 24, 24);
    $('.error').html("<a class='close' data-dismiss='alert'>&times;</a> Sum of squared errors: "+ error.toFixed(2));
  }
  else if (event.which == 115) {
    // down
    c_temp[1]+=1;
    ctx_second.drawImage(image_second,0,0,si_width,si_height,0,0,canvas_second.width(),canvas_second.height())
    error=compute_error(c_temp[0], c_temp[1]);
    x=c_temp[0]-12;
    y=c_temp[1]-12;
    ctx_second.strokeRect(x, y, 24, 24);
    $('.error').html("<a class='close' data-dismiss='alert'>&times;</a> Sum of squared errors: "+ error.toFixed(2));
  }
  else if (event.which == 13) {
    // enter
	$('.c3').removeClass('active');
	$('.c1').addClass('active');
	$('body').unbind('keypress');
	c.push(c_temp[0],c_temp[1]);
	errors.push(error);
	c_temp.length=0;
	canvas_first.bind('click', canvas_first_mouseclick);
	deliver_message("Good Job! Ready to go again? Choose the next Feature Point in the first Frame.")
	$(".control p.count").html("You have found " + c.length/4 + " correspondences.");
	print_correspondence_table();
  }
}

function print_correspondence_table() {
  str = "<table class='table table-condensed table striped'>";
  str += "<tr><th>x1</th><th>y1</th><th>x2</th><th>y2</th><th>error</th><th></th></tr>"
  for (i=0;i<errors.length;i++) {
    c_index = i*4;
    str += "<tr class='value' id='"+i+"'><td>"+c[c_index]+"</td><td>"+c[c_index+1]+"</td><td>"+c[c_index+2]+"</td><td>"+c[c_index+3]+"</td><td>"+errors[i].toFixed(2)+"</td><td><a href='#' class='removec'><i class='icon-trash'></i></a></tr>";
  }
  str += "</table>";
  $(".control .ctable").html(str);
}

function highlight_correspondence(i) {
  ctx_first.drawImage(image_first,0,0,fi_width,fi_height,0,0,canvas_first.width(),canvas_first.height())
  ctx_second.drawImage(image_second,0,0,si_width,si_height,0,0,canvas_second.width(),canvas_second.height())
  i=i*4;
  ctx_first.beginPath();
  ctx_first.arc(c[i],c[i+1],3,0,Math.PI*2,false);
  ctx_first.closePath();
  ctx_first.stroke();
  ctx_second.beginPath();
  ctx_second.arc(c[i+2],c[i+3],3,0,Math.PI*2,false);
  ctx_second.closePath();
  ctx_second.stroke();
}

function get_url_param(name){
  //Parsing of URL parameters
  name = name.replace(/[\[]/,"\\\[").replace(/[\]]/,"\\\]");
  var regexS = "[\\?&]"+name+"=([^&#]*)";
  var regex = new RegExp( regexS );
  var results = regex.exec(window.location.href);
  if( results == null)
    return "";
  else
    return results[1];
}

function get_duration() {
  return begin_time.toTimeString()+"_"+(new Date()).toTimeString();
}

function get_results() {
  //Compute difference 
  feature_points = c.map(function(elem) { return elem/(canvas_first.height()/fi_height) });
  if (feature_points.length==0) {
    return "";
  }
  return get_url_param('images') + ',' + feature_points.join(",");
}

function submit_results(){
  if (c.length/4 == 8) {
	  var result = get_results();
	  var duration = get_duration();
	  document.getElementById('correspondences').value = result;
	  document.getElementById('duration').value = duration;
	  document.forms["mturk_form"].submit();
	  //alert([result, duration]);
	}
  else {
	deliver_message("Not enough points! Please continue.");
  	}

}

function remove_correspondence(cindex) {
  c.remove(cindex*4,cindex*4+3);
  errors.remove(cindex);
  draw_correspondences();
  print_correspondence_table();
}
