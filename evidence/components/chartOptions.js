// Defaults for every cartesian chart. ECharts sizes axis labels in a fallback
// font unless the label names one, and the last label on the x axis can run
// past the default right padding on narrow screens.
const base = {
	grid: { right: 18 },
	xAxis: { axisLabel: { fontFamily: 'Inter, sans-serif' } },
	yAxis: { axisLabel: { fontFamily: 'Inter, sans-serif' } }
};

const isObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

function merge(under, over) {
	const out = { ...under };
	for (const [key, value] of Object.entries(over)) {
		out[key] = isObject(value) && isObject(out[key]) ? merge(out[key], value) : value;
	}
	return out;
}

// Per-chart settings win over the defaults.
export const ajusteGrafico = (extra = {}) => merge(base, extra);
