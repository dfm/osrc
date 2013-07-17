(function () {

  "use strict";

  var cb = d3.scale.category10();

  window.histogram = function () {
    var width = 200,
        height = 150,
        margin = 20,
        labels = [];

    var hist = function (selection) {
      selection.each(function (data) {
        // Compute the stacking offsets.
        data = data.map(function (d0) {
          var y0 = 0;
          return d0.map(function (d, i) {
            var o = {y: d, y0: y0}
            y0 += d;
            return o;
          });
        });

        var bar_width = (width - 30) / data.length;

        var ylim = [0, d3.max(data, function (d) {
          return d3.sum(d, function (d0) { return d0.y; });
        })];

        var x = d3.scale.linear()
                  .range([0.5*bar_width, width-0.5*bar_width])
                  .domain([0, data.length]),
            y = d3.scale.linear()
                  .range([height, 0])
                  .domain(ylim);

        var el = d3.select(this),
            sel = el.selectAll("svg").data([data]);
        sel.enter().append("svg")

        sel.attr("width", width)
           .attr("height", height+margin);

        var axis = sel.selectAll("line.axis").data([[0, width]]);
        axis.enter().append("line").attr("class", "axis");
        axis.attr("x1", function (d) { return d[0]; })
            .attr("x2", function (d) { return d[1]; })
            .attr("y1", height)
            .attr("y2", height);
        axis.exit().remove();

        var bars = sel.selectAll("g").data(data),
            gs = bars.enter().append("g");

        gs.append("text");
        data[0].map(function (d, i, b) {
          gs.append("rect")
              .attr("data-ind", i)
        });

        bars.attr("transform", function (d, i) {
          return "translate("+x(i)+",0)";
        });

        bars.selectAll("rect")
            .style("fill", function (d) {
              var ind = d3.select(this).attr("data-ind");
              return cb(ind);
            })
            .attr("x", 0)
            .attr("width", bar_width)
            .attr("y", function (d) {
              var ind = d3.select(this).attr("data-ind");
              return y(d[ind].y0 + d[ind].y);
            })
            .attr("height", function (d) {
              var ind = d3.select(this).attr("data-ind");
              return height - y(d[ind].y);
            });

        if (labels.length == data.length) {
          bars.select("text")
            .text(function (d, i) { return labels[i]; })
            .attr("y", height)
            .attr("dy", 12)
            .attr("x", 0.5*bar_width)
            .attr("text-anchor", "middle");
        }

        bars.exit().remove();

        sel.exit().remove();
      })
    };

    hist.width = function (value) {
      if (!arguments.length) return width;
      width = value;
      return hist;
    };

    hist.height = function (value) {
      if (!arguments.length) return height;
      height = value;
      return hist;
    };

    hist.margin = function (value) {
      if (!arguments.length) return margin;
      margin = value;
      return hist;
    };

    hist.labels = function (value) {
      if (!arguments.length) return labels;
      labels = value;
      return hist;
    };

    return hist;
  };

  window.piechart = function () {
    var dim = 200, margin = 50;

    var pie = function (selection) {
      selection.each(function (data) {
        var el = d3.select(this),
            sel = el.selectAll("svg").data([data]),
            arc = d3.svg.arc()
                    .outerRadius(0.5 * dim)
                    .innerRadius(0),
            plo = d3.layout.pie()
                    .sort(null)
                    .value(function(d) { return d; });

        sel.enter().append("svg")

        var g = sel
                    .attr("width", dim + margin)
                    .attr("height", dim + margin)
                   .append("g")
                    .attr("transform", "translate("+0.5*(dim+margin)+","
                          +0.5*(dim+margin)+")");

        var arcs = g.selectAll(".arc")
                      .data(plo(data))
                    .enter().append("g")
                      .attr("class", "arc");

        arcs.append("path")
            .attr("d", arc)
            .style("fill-opacity", 0.8)
            .style("fill", function(d, i) { return cb(i); });

        arcs.append("text")
          .attr("transform", function(d) {
            var v = arc.centroid(d),
                norm = Math.sqrt(v[0]*v[0] + v[1]*v[1]);
            v[0] *= 2.25;
            v[1] *= 2.25;
            return "translate("+v+")";
          })
          .attr("dy", ".35em")
          .style("text-anchor", "middle")
          .text(function(d) { return d.data; })
          .style("stroke", function(d, i) { return cb(i); });

        sel.exit().remove();
      })
    };

    pie.dim = function (value) {
      if (!arguments.length) return dim;
      dim = value;
      return pie;
    };

    return pie;
  };

})();
