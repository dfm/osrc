(function () {

  "use strict";

  window.histogram = function () {
    var width = 200,
        height = 150,
        margin = 20,
        labels = [];

    var hist = function (selection) {
      selection.each(function (data) {
        var bar_width = (width - 30) / data.length;

        var ylim = [0, d3.max(data)];

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

        gs.append("rect");
        gs.append("text");

        bars.attr("transform", function (d, i) {
          return "translate("+x(i)+",0)";
        })

        bars.select("rect")
            .attr("x", 0)
            .attr("width", bar_width)
            .attr("y", function (d) { return y(d); })
            .attr("height", function (d) { return height - y(d); });
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

})();
