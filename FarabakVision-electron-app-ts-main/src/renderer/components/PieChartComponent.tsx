import { Pie, PieChart } from "recharts";

const PieChartComponent: React.FC<{
  data: { name: string; value: number; fill: string }[]; dataKey?: string
}> = ({ data }) => {
  return (
    <PieChart
      style={{
        width: "100%",
        maxWidth: "200px",
        maxHeight: "80vh",
        aspectRatio: 1,
      }}
      responsive
    >
      <Pie
        data={data}
        innerRadius="80%"
        outerRadius="100%"
        // Corner radius is the rounded edge of each pie slice
        cornerRadius="50%"
        // padding angle is the gap between each pie slice
        paddingAngle={5}
        dataKey="value"
        isAnimationActive={true}
        animationEasing="ease-in-out"
        stroke="none"
      />
    </PieChart>
  );
};

export default PieChartComponent;
