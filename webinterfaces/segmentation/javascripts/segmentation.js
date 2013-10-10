// {{{ stolen functions
//{{{ Array Remove - By John Resig (MIT Licensed)
Array.prototype.remove = function(from, to) {
  var rest = this.slice((to || from) + 1 || this.length);
  this.length = from < 0 ? this.length + from : from;
  return this.push.apply(this, rest); //}}}

$.fn.spin = function(opts) { //{{{ Spinner for Jquery
  this.each(function() {
    var $this = $(this),
        data = $this.data();

    if (data.spinner) {
      data.spinner.stop();
      delete data.spinner;
    }
    if (opts !== false) {
      data.spinner = new Spinner($.extend({color: $this.css('color')}, opts)).spin(this);
    }
  });
  return this;
};//}}}

}; //}}}

//{{{ Variables
var img
var canvas_fix;
var canvas_firstframe;
var ctx;
var ctx_firstframe;
var canvas_width = 400;
var canvas_height = 400;
var image_name;
var category_name;

var viewport_top_left_x;
var viewport_top_left_y;
var viewport_height;
var viewport_width;
var max_viewport_x;
var max_viewport_y;

var begin_time="";

var base_url = '..';
//var base_url = 'http://restlesscat_mturk.s3.amazonaws.com';
//var base_url = ".";

//polygon coordinates
var x = new Array();
var y = new Array();

var numpts=0;

//tolerance radius
var tr=5;

//drawing styles
var linecolor = "rgba(255,0,0,0.9)";
var linewidth = 1.0;
var pt_size   = 2.0;
var pt_color  = "rgba(0,0,255,0.9)";

// closed or open polygon
var polygon_is_closed = true;
// adjusted or left as-is polygon
var polygon_is_adjusted = false;

var is_original_image = true;

// index of the point selected
var selected_idx = -1; //}}}

//{{{ Utility functions
function t_distance(a_x,a_y,b_x,b_y) {
  return Math.sqrt(Math.pow(b_x-a_x,2) + Math.pow(b_y-a_y,2));
}

function pred_index(i, arr) { // get index of predecessor
  return i == 0 ? arr.length-1 : i-1;
}

function find_appropriate_edge(x_val,y_val) {
  ratios=x.map(function(elem, i) {
    return t_distance(x[i], y[i], x_val, y_val) + t_distance(x[pred_index(i,x)], y[pred_index(i,y)], x_val, y_val) - t_distance(x[i], y[i], x[pred_index(i,x)], y[pred_index(i,y)]);
  });
  smallest = ratios[0];
  i=0;
  ratios.forEach(function(elem, index) {
    if (elem < smallest) {
      smallest = elem;
      i = index;
    }
  });
  return i;
}
//}}}

//{{{ Slider
var zoom = 1;
var options = {
  value:1,
  min: 1,
  max: 4,
  step: 0.1,
  slide: function(event, ui) {
    zoom = ui.value;
    $("#zoom").html(zoom);
    viewport_height = true_image_height/zoom;
    viewport_width = true_image_width/zoom;
    max_viewport_x = true_image_width-viewport_width;
    max_viewport_y = true_image_height-viewport_height;
    draw_canvas();
  },
  change: function(event, ui) {
    zoom = ui.value;
    $("#zoom").html(zoom);
  }
}//}}}

//{{{ Spinner options
var opts = {
  lines: 12, // The number of lines to draw
  length: 7, // The length of each line
  width: 4, // The line thickness
  radius: 10, // The radius of the inner circle
  color: '#000', // #rgb or #rrggbb
  speed: 1, // Rounds per second
  trail: 60, // Afterglow percentage
  shadow: false, // Whether to render a shadow
  hwaccel: false // Whether to use hardware acceleration
}; //}}}

$(document).ready(function() {
  $("#no-hint").hide();
  $("#hint").focus(function() {
    $("#no-hint").show();
    $("#hint").hide();
    $("#no-hint").focus();
  });
  $("#slider").slider(options);
  $("#zoom").html($("#slider").slider("value"));
  $("#segmentation_canvas").mouseleave(mouseup_canvas);
  document.getElementById('change_contrast').disabled = true;
  $("#slider, #segmentation_canvas").bind("mousewheel", function(event, delta) {
    $("#slider").slider("value", $("#slider").slider("value") + delta * 0.1);
    center_x = viewport_top_left_x + viewport_width/2;
    center_y = viewport_top_left_y + viewport_height/2;
    viewport_height = true_image_height/zoom;
    viewport_width = true_image_width/zoom;
    max_viewport_x = true_image_width-viewport_width;
    max_viewport_y = true_image_height-viewport_height;
    viewport_top_left_x = center_x - viewport_width/2;
    viewport_top_left_y = center_y - viewport_height/2;
    if (viewport_top_left_x < 0)
      viewport_top_left_x = 0;
    if (viewport_top_left_y < 0)
      viewport_top_left_y = 0;
    if (viewport_top_left_x > max_viewport_x)
      viewport_top_left_x = max_viewport_x;
    if (viewport_top_left_y > max_viewport_y)
      viewport_top_left_y = max_viewport_y;
    draw_canvas();
    return false;
  });

  //{{{ Insert Node ond dblclick
  $("#segmentation_canvas").bind("dblclick", function(event) {
    closest_point=get_closest_point_idx(event);
    if (closest_point>0) {
      x.remove(closest_point);
      y.remove(closest_point);
      numpts=x.length;
      draw_canvas(event);
    }
    else{
      img_coords_x=screen_to_image_x(event.pageX);
      img_coords_y=screen_to_image_y(event.pageY);
      index = find_appropriate_edge(img_coords_x, img_coords_y);
      x.splice(index, 0, img_coords_x);
      y.splice(index, 0, img_coords_y);
      numpts++;
      draw_polygon();
    }
  }); //}}}

  // {{{ Init
  init_canvas();
  document.getElementById('assignmentId').value = gup('assignmentId');

  // Check if the worker is PREVIEWING the HIT or if they've ACCEPTED the HIT
  if (gup('assignmentId') == "ASSIGNMENT_ID_NOT_AVAILABLE")
  {
    // If we're previewing, disable the button and give it a helpful message
    document.getElementById('submitButton').disabled = true;
    document.getElementById('submitButton').value = "You must ACCEPT the HIT before you can submit the results.";
  } else {
    var form = document.getElementById('mturk_form');
    if (document.referrer && ( document.referrer.indexOf('workersandbox') != -1) ) {
      form.action = "http://workersandbox.mturk.com/mturk/externalSubmit";
    }
  } //}}}
});

//{{{ Original Script
function init_canvas(){//{{{ init function
  img = new Image();
  flipped_img = new Image();
  original_img = new Image();
  firstframe_img = new Image();
  var cat_img_name = get_category_image_name();
  // tokenize the category and image name based on comma
  var tokens = cat_img_name.split(',');
  category_name = tokens[0];
  image_name    = tokens[1];
  original_img.src = base_url + '/' + category_name + '/' + image_name;
  flipped_img.src = base_url + '/' + category_name + '/flipped_' + image_name;
  firstframe_img.src = base_url + '/' + category_name + '/FirstFrames/' + tokens[1].split("_")[2]+".png";
  img = original_img;
  true_image_width = img.width;
  true_image_height = img.height;
  viewport_height = true_image_height;
  viewport_width = true_image_width;
  var corr_factor = canvas_width/true_image_width;
  max_viewport_x = 0;
  max_viewport_y = 0;
  viewport_top_left_x = 0;
  viewport_top_left_y = 0;
  canvas_fix = document.getElementById("segmentation_canvas");
  canvas_firstframe = document.getElementById("firstframe_canvas");
  canvas_fix.width = canvas_width;//true_image_width;
  canvas_fix.height = canvas_height;//true_image_height;
  canvas_firstframe.width = canvas_width; //true_image_width;
  canvas_firstframe.height = canvas_height;//true_image_height;
  ctx = canvas_fix.getContext("2d");
  ctx_firstframe = canvas_firstframe.getContext("2d");	
  canvas_fix.onmousedown = mousedown_canvas;
  canvas_fix.onmousemove = mousemove_canvas;
  canvas_fix.onmouseup   = mouseup_canvas;
  initialize_polygon();
  //img.onload = draw_image;
  firstframe_img.onload = draw_firstframe_image;
  draw_canvas();
}
//}}}

function draw_canvas(){
  ctx.clearRect(0, 0, true_image_width, true_image_height);
  draw_image();
  draw_firstframe_image();
  draw_polygon();
}


function draw_image(){
  ctx.drawImage(img, viewport_top_left_x, viewport_top_left_y, viewport_width, viewport_height, 0, 0, canvas_width, canvas_height);
}

function draw_firstframe_image(){
  ctx_firstframe.drawImage(firstframe_img, 0, 0, firstframe_img.width, firstframe_img.height, 0, 0, canvas_width, canvas_height);

  //Draw white viewport rectangle
  ctx_firstframe.strokeStyle = "white";
  ctx_firstframe.lineWidth = 2.0;
  ctx_firstframe.beginPath();
  ctx_firstframe.moveTo(viewport_top_left_x*(canvas_width/firstframe_img.width) , viewport_top_left_y*(canvas_width/firstframe_img.width));
  ctx_firstframe.lineTo(viewport_top_left_x*(canvas_width/firstframe_img.width) + viewport_width*(canvas_width/firstframe_img.width), viewport_top_left_y*(canvas_width/firstframe_img.width));
  ctx_firstframe.lineTo(viewport_top_left_x*(canvas_width/firstframe_img.width) + viewport_width*(canvas_width/firstframe_img.width), viewport_top_left_y*(canvas_width/firstframe_img.width) + viewport_height*(canvas_width/firstframe_img.width));
  ctx_firstframe.lineTo(viewport_top_left_x*(canvas_width/firstframe_img.width), viewport_top_left_y*(canvas_width/firstframe_img.width) + viewport_height*(canvas_width/firstframe_img.width));
  ctx_firstframe.lineTo(viewport_top_left_x*(canvas_width/firstframe_img.width), viewport_top_left_y*(canvas_width/firstframe_img.width));
  ctx_firstframe.stroke();	
}

function get_x_vp(i) {
  return image_to_viewport_x(x[i]);
}

function get_y_vp(i) {
  return image_to_viewport_y(y[i]);
}

function get_x(i) {
  return x[i];
}
function get_y(i) {
  return y[i];
}
function set_x(i, val) {
  x[i] = val;
}
function set_y(i, val) {
  y[i] = val;
}

// get bounding rectangle center x coordinate
function get_center_x(){
  total = 0;
  for(i=0; i<numpts; i++){
    total += get_x(i);
  }
  return (total/numpts);
}

// get bounding rectangle center y coordinate
function get_center_y(){
  total = 0;
  for(i=0; i<numpts; i++){
    total += get_y(i);
  }
  return (total/numpts);
}

function get_center_x_vp() {
  return image_to_viewport_x(get_center_x());
}

function get_center_y_vp() {
  return image_to_viewport_y(get_center_y());
}

function get_min_x(){
  min = 100000;
  for(i=0; i<numpts; i++){
    if(get_x(i)<min)
      min = get_x(i);
  }
  return (min);
}

function get_min_x_vp() {
  return image_to_viewport_x(get_min_x());
}

function get_max_x(){
  max = -1;
  for(i=0; i<numpts; i++){
    if(get_x(i)>max)
      max = get_x(i);
  }
  return (max);
}

function get_max_x_vp() {
  return image_to_viewport_x(get_max_x());
}

function get_min_y(){
  min = 100000;
  for(i=0; i<numpts; i++){
    if(get_y(i)<min)
      min = get_y(i);
  }
  return (min);
}

function get_min_y_vp() {
  return image_to_viewport_y(get_min_y());
}

function get_max_y(){
  max = -1;
  for(i=0; i<numpts; i++){
    if(get_y(i)>max)
      max = get_y(i);
  }
  return (max);
}

function get_max_y_vp() {
  return image_to_viewport_y(get_max_y());
}


// reset the annotation
function reset_annotation(){
  selected_idx = -1;
  polygon_is_adjusted = false;
  x = new Array();
  y = new Array();
  numpts = 0;
  initialize_polygon();
  draw_canvas();
}

//change image contrast
function change_contrast(){
  if(is_original_image){
    img = flipped_img;
    is_original_image = false;
  } else{
    img = original_img;
    is_original_image = true;
  }
  draw_canvas();
}

// true if the point is close to the start
function is_close_to_start(event){
  if(numpts > 0){
    var d2 = Math.pow((screen_to_image_x(event.pageX)-get_x(0)),2) + Math.pow((screen_to_image_y(event.pageY-get_y(0)), 2));
    return d2 < tr*tr;
  }else{
    return false;
  }
}

// returns the index of the point close to the current one (within tr) {{{
function get_closest_point_idx(event){
  vx=screen_to_viewport_x(event.pageX);
  vy=screen_to_viewport_y(event.pageY);
  var idx = -1;
  var min_dist = 100000000;
  for(var i=0;i<numpts;i++){
    var d2 = (vx-get_x_vp(i))*(vx-get_x_vp(i)) + (vy-get_y_vp(i))*(vy-get_y_vp(i));
    if(d2 < min_dist){
      min_dist = d2;
      idx = i;
    }
  }
  if(min_dist < tr*tr){
    return idx;
  }
  else if((vx-get_center_x_vp())*(vx-get_center_x_vp()) + (vy-get_center_y_vp())*(vy-get_center_y_vp()) < tr*tr){
    return -2;
  }
  else if((vx-(get_max_x_vp()+10))*(vx-(get_max_x_vp()+10)) + (vy-get_center_y_vp())*(vy-get_center_y_vp()) < tr*tr){
    return -3;
  }
  else if((vx-(get_min_x_vp()-10))*(vx-(get_min_x_vp()-10)) + (vy-get_center_y_vp())*(vy-get_center_y_vp()) < tr*tr){
    return -4;
  }
  else if((vx-get_center_x_vp())*(vx-get_center_x_vp()) + (vy-(get_max_y_vp()+10))*(vy-(get_max_y_vp()+10)) < tr*tr){
    return -5;
  }
  else if((vx-get_center_x_vp())*(vx-get_center_x_vp()) + (vy-(get_min_y_vp()-10))*(vy-(get_min_y_vp()-10)) < tr*tr){
    return -6;
  }
  else{
    return -1;
  }
}
//}}}

// draw the current point
function draw_current_point(r){
  ctx.fillStyle = pt_color;
  ctx.fillRect(cx-r,cy-r,2*r,2*r);
}

//{{{ draw the polygon
function draw_polygon(){
  ctx.strokeStyle = linecolor;
  ctx.lineWidth = linewidth;
  for(i = 0; i < numpts-1; i++){
    ctx.beginPath();
    ctx.moveTo(get_x_vp(i),get_y_vp(i));
    ctx.lineTo(get_x_vp(i+1),get_y_vp(i+1));
    ctx.stroke();

  }
  for(i = 0; i < numpts; i++){
    ctx.fillStyle = pt_color;
    ctx.fillRect(get_x_vp(i)-pt_size,get_y_vp(i)-pt_size,2*pt_size,2*pt_size);
  }
  if(numpts > 0){
    if(polygon_is_closed){
      ctx.beginPath();
      ctx.moveTo(get_x_vp(numpts-1),get_y_vp(numpts-1));
      ctx.lineTo(get_x_vp(0),get_y_vp(0)); // the current location
      ctx.stroke();
      // draw polygon center
      ctx.beginPath();
      ctx.lineWidth = 3;
      ctx.moveTo(get_center_x_vp()-5, get_center_y_vp());
      ctx.lineTo(get_center_x_vp()+5, get_center_y_vp());
      ctx.moveTo(get_center_x_vp(), get_center_y_vp()-5);
      ctx.lineTo(get_center_x_vp(), get_center_y_vp()+5);
      // draw N, E, S and W handles
      ctx.moveTo(get_max_x_vp()+10, get_center_y_vp());
      ctx.lineTo(get_max_x_vp()+15, get_center_y_vp());
      ctx.moveTo(get_max_x_vp()+10, get_center_y_vp()-10);
      ctx.lineTo(get_max_x_vp()+10, get_center_y_vp()+10);

      ctx.moveTo(get_min_x_vp()-10, get_center_y_vp());
      ctx.lineTo(get_min_x_vp()-15, get_center_y_vp());
      ctx.moveTo(get_min_x_vp()-10, get_center_y_vp()-10);
      ctx.lineTo(get_min_x_vp()-10, get_center_y_vp()+10);

      ctx.moveTo(get_center_x_vp(), get_max_y_vp()+10);
      ctx.lineTo(get_center_x_vp(), get_max_y_vp()+15);
      ctx.moveTo(get_center_x_vp()-10, get_max_y_vp()+10);
      ctx.lineTo(get_center_x_vp()+10, get_max_y_vp()+10);

      ctx.moveTo(get_center_x_vp(), get_min_y_vp()-10);
      ctx.lineTo(get_center_x_vp(), get_min_y_vp()-15);
      ctx.moveTo(get_center_x_vp()-10, get_min_y_vp()-10);
      ctx.lineTo(get_center_x_vp()+10, get_min_y_vp()-10);
      ctx.stroke();
    }else{
      ctx.beginPath();
      ctx.moveTo(get_x_vp(numpts-1),get_y_vp(numpts-1));
      ctx.lineTo(cx,cy); // the current location
      ctx.stroke();
      if(is_close_to_start(event)) {
        draw_current_point(2*pt_size);
      }
      else {
        draw_current_point(pt_size);
      }
    }
  }
}//}}}

// GUI input handling
// {{{ Point conversion between screen image and viewport
function viewport_to_image_x(coord) {
  return viewport_top_left_x + coord/zoom/(canvas_width/true_image_width);
}

function viewport_to_image_y(coord) {
  return viewport_top_left_y + coord/zoom/(canvas_width/true_image_width);
}

function screen_to_viewport_x(coord) {
  return coord - $('#segmentation_canvas').offset().left;
}

function screen_to_viewport_y(coord) {
  return coord - $('#segmentation_canvas').offset().top;
}

function screen_to_image_x(coord) {
  return viewport_to_image_x(screen_to_viewport_x(coord));
}

function screen_to_image_y(coord) {
  return viewport_to_image_y(screen_to_viewport_y(coord));
}

function image_to_viewport_x(coord) {
  return (coord-viewport_top_left_x)*zoom*(canvas_width/true_image_width);
}

function image_to_viewport_y(coord) {
  return (coord-viewport_top_left_y)*zoom*(canvas_width/true_image_width);
} // }}}

function mouseup_canvas(event){
  $("#segmentation_canvas").css('cursor', 'default');
  canvas_fix.onmousemove=mousemove_canvas;
  event.preventDefault();
  event.stopPropagation();
  if(polygon_is_closed){
    selected_idx = -1;
  }else{
    if(is_close_to_start(event)){
      polygon_is_closed = true;
      selected_idx = -1;
    }else{
      set_x(numpts,screen_to_image_x(event.pageX));
      set_y(numpts,screen_to_image_y(event.pageY));
      numpts = numpts + 1;
      draw_canvas();
    }
  }
}

function mousedown_canvas(event){
  selected_idx = get_closest_point_idx(event);
  start_mouse_x=screen_to_viewport_x(event.pageX);
  start_mouse_y=screen_to_viewport_y(event.pageY);
  start_viewport_x=viewport_top_left_x;
  start_viewport_y=viewport_top_left_y;
  orig_x = x.slice();
  orig_y = y.slice();
  if (selected_idx == -1) {
    canvas_fix.onmousemove = mousemove_drag;
    $("#segmentation_canvas").css('cursor', 'hand');
  }
  else 
    $("#segmentation_canvas").css('cursor', 'crosshair');
  event.preventDefault();
}

function mousemove_drag(event) {
  viewport_top_left_x=start_viewport_x+(start_mouse_x-screen_to_viewport_x(event.pageX))/zoom/(canvas_width/true_image_width);
  viewport_top_left_y=start_viewport_y+(start_mouse_y-screen_to_viewport_y(event.pageY))/zoom/(canvas_width/true_image_width);
  if (viewport_top_left_x < 0)
    viewport_top_left_x = 0;
  if (viewport_top_left_y < 0)
    viewport_top_left_y = 0;
  if (viewport_top_left_x > max_viewport_x)
    viewport_top_left_x = max_viewport_x;
  if (viewport_top_left_y > max_viewport_y)
    viewport_top_left_y = max_viewport_y;
  event.stopPropagation();
  draw_canvas();
}

//update the current location of the keypoint
function mousemove_canvas(event){
  ix = screen_to_image_x(event.pageX);
  iy = screen_to_image_y(event.pageY)
  vx = screen_to_viewport_x(event.pageX);
  vy = screen_to_viewport_y(event.pageY);

  if(polygon_is_closed && selected_idx >= 0){
    x[selected_idx]=ix;
    y[selected_idx]=iy;
  } else if(polygon_is_closed && selected_idx == -2){
    distance_x = (start_mouse_x-vx)/zoom/(canvas_width/true_image_width);
    distance_y = (start_mouse_y-vy)/zoom/(canvas_width/true_image_width);
    move_polygon(distance_x,distance_y);
  } else if(polygon_is_closed && selected_idx == -3){
    distance = ix-get_max_x()-5;
    stretch_polygon(distance,-3);
  } else if(polygon_is_closed && selected_idx == -4){
    distance = ix-get_min_x()+5;
    stretch_polygon(distance,-4);
  } else if(polygon_is_closed && selected_idx == -5){
    distance = iy-get_max_y()-5;
    stretch_polygon(distance,-5);
  } else if(polygon_is_closed && selected_idx == -6){
    distance = iy-get_min_y()+5;
    stretch_polygon(distance,-6);
  }
  draw_canvas();
  polygon_is_adjusted = true;
  if(begin_time == ""){
    var time = new Date();
    var hours = time.getHours();
    var minutes = time.getMinutes();
    var seconds = time.getSeconds();
    begin_time = hours+"/"+minutes+"/"+seconds;
  }
  event.preventDefault();
}

function move_polygon(distance_x,distance_y){
  for(var i=0;i<numpts;i++){
    x[i]=orig_x[i]-distance_x;
    y[i]=orig_y[i]-distance_y;
  }
}

function stretch_polygon(distance, direction){
  var center_x = get_center_x();
  var center_y = get_center_y();
  var min_x = get_min_x();
  var max_x = get_max_x();
  var min_y = get_min_y();
  var max_y = get_max_y();
  var x_span = max_x-min_x;
  var y_span = max_y-min_y;
  if(direction == -3){ // right
    for(i=0; i<numpts; i++){
      var current = get_x(i);
      if (x_span==0) {
        x_span=0.1;
        var scale_factor = 1;
      }
      else
        var scale_factor = (current-min_x)/x_span;
      x[i]=current+distance*scale_factor;
    }
  } else if(direction == -4){ // left
    for(i=0; i<numpts; i++){
      var current = get_x(i);
      if (x_span==0){
        x_span=0.1;
        var scale_factor = 1;
      }
      else
        var scale_factor = (max_x-current)/x_span;
      x[i]=current+distance*scale_factor;
    }
  } else if(direction == -5){ // up
    for(i=0; i<numpts; i++){
      var current = get_y(i);
      if (y_span==0) {
        y_span=0.1;
        var scale_factor = 1;
      }
      else
        var scale_factor = (current-min_y)/y_span;
      y[i]=current+distance*scale_factor;
    }
  } else if(direction == -6){ // down
    for(i=0; i<numpts; i++){
      var current = get_y(i);
      if (y_span==0) {
        y_span=0.1;
        var scale_factor = 1;
      }
      else
        var scale_factor = (max_y-current)/y_span;
      y[i]=current+distance*scale_factor;
    }
  }
  console.log(distance*scale_factor);
}

// functions related to AMT task
function gup(name){
  var regexS = "[\\?&]"+name+"=([^&#]*)";
  var regex = new RegExp( regexS );
  var tmpURL = window.location.href;
  var results = regex.exec( tmpURL );
  if( results == null )
    return "";
  else
    return results[1];
}

// what to submit to AMT server
function get_results_string(){
  var result = category_name + "," + image_name;
  for(var i=0;i<numpts;i++){
    result +=  "," + x[i] + "," + y[i];
  }
  return result;
}

// grab the results and submit to the server
function submitResults(){
  if(!polygon_is_closed){
    alert("Please close the polygon before submitting.");
    return;
  }
  if(!polygon_is_adjusted){
    alert("You haven't adjusted any points.");
    return;
  }

  var results = get_results_string();
  var duration = getDuration();
  document.getElementById('segpoly').value = results;
  document.getElementById('duration').value = duration;
  document.forms["mturk_form"].submit();
  //alert(results);
}

function getDuration(){
  var time = new Date();
  var hours = time.getHours();
  var minutes = time.getMinutes();
  var seconds = time.getSeconds();
  var result = begin_time+"_"+hours+"/"+minutes+"/"+seconds;
  return result;
}

function get_category_image_name(){
  var cat_img_name = gup('category-image-polygon');
  if(cat_img_name == ""){cat_img_name = "images,car.png";}
  return cat_img_name;
}

function initialize_polygon(){
  var polygon = gup('category-image-polygon');
  if(polygon == ""){polygon = "98.299,77.583,111.878,76.725,117.624,77.374";}
  
  var tokens = polygon.split(',');
  var offset = tokens[1].split('_');
  
  for(var i=2;i<tokens.length;i=i+2){
    x[numpts] = parseFloat(tokens[i]) - parseFloat(offset[0]);
    y[numpts] = parseFloat(tokens[i+1]) - parseFloat(offset[1]);
    numpts = numpts+1;
  }
} //}}}
