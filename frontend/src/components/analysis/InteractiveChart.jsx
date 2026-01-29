import React, { useRef, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar, Pie, Scatter } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const InteractiveChart = ({ chartData, chartType }) => {
  const chartRef = useRef(null);

  if (!chartData || !chartData.data) {
    return <div className="text-slate-500 text-center py-8">No data available</div>;
  }

  const data = chartData.data;

  // Prepare data based on chart type
  const prepareChartData = () => {
    switch (data.type) {
      case 'line':
        return {
          labels: data.labels || [],
          datasets: [{
            label: data.yLabel || 'Values',
            data: data.values || [],
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.3,
            fill: true,
            pointRadius: 5,
            pointHoverRadius: 7,
            pointBackgroundColor: 'rgb(59, 130, 246)',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointHoverBackgroundColor: 'rgb(37, 99, 235)',
            pointHoverBorderColor: '#fff',
          }]
        };

      case 'bar':
      case 'horizontal_bar':
        return {
          labels: data.labels || [],
          datasets: [{
            label: data.yLabel || 'Values',
            data: data.values || [],
            backgroundColor: 'rgba(59, 130, 246, 0.7)',
            borderColor: 'rgb(59, 130, 246)',
            borderWidth: 2,
            hoverBackgroundColor: 'rgba(37, 99, 235, 0.9)',
            hoverBorderColor: 'rgb(29, 78, 216)',
          }]
        };

      case 'histogram':
        // Calculate histogram bins
        const values = data.values || [];
        const bins = 30;
        const min = Math.min(...values);
        const max = Math.max(...values);
        const binWidth = (max - min) / bins;
        const binCounts = new Array(bins).fill(0);
        const binLabels = [];

        for (let i = 0; i < bins; i++) {
          binLabels.push(`${(min + i * binWidth).toFixed(1)}`);
        }

        values.forEach(value => {
          const binIndex = Math.min(Math.floor((value - min) / binWidth), bins - 1);
          binCounts[binIndex]++;
        });

        return {
          labels: binLabels,
          datasets: [{
            label: data.yLabel || 'Frequency',
            data: binCounts,
            backgroundColor: 'rgba(99, 102, 241, 0.7)',
            borderColor: 'rgb(99, 102, 241)',
            borderWidth: 2,
            hoverBackgroundColor: 'rgba(79, 70, 229, 0.9)',
          }]
        };

      case 'scatter':
        const scatterData = (data.x || []).map((x, i) => ({
          x: x,
          y: data.y[i]
        }));

        return {
          datasets: [{
            label: 'Data Points',
            data: scatterData,
            backgroundColor: 'rgba(147, 51, 234, 0.7)',
            borderColor: 'rgb(147, 51, 234)',
            pointRadius: 5,
            pointHoverRadius: 8,
            pointBorderWidth: 2,
            pointHoverBorderWidth: 3,
          }]
        };

      case 'pie':
        const colors = [
          'rgba(239, 68, 68, 0.8)',
          'rgba(59, 130, 246, 0.8)',
          'rgba(34, 197, 94, 0.8)',
          'rgba(251, 191, 36, 0.8)',
          'rgba(168, 85, 247, 0.8)',
          'rgba(236, 72, 153, 0.8)',
          'rgba(20, 184, 166, 0.8)',
          'rgba(249, 115, 22, 0.8)',
        ];

        return {
          labels: data.labels || [],
          datasets: [{
            data: data.values || [],
            backgroundColor: colors,
            borderColor: colors.map(c => c.replace('0.8', '1')),
            borderWidth: 2,
            hoverOffset: 15,
          }]
        };

      case 'grouped_bar':
        return {
          labels: data.projects || [],
          datasets: [
            {
              label: 'Mean',
              data: data.mean || [],
              backgroundColor: 'rgba(59, 130, 246, 0.7)',
              borderColor: 'rgb(59, 130, 246)',
              borderWidth: 2,
              hoverBackgroundColor: 'rgba(37, 99, 235, 0.9)',
            },
            {
              label: 'Median',
              data: data.median || [],
              backgroundColor: 'rgba(251, 191, 36, 0.7)',
              borderColor: 'rgb(251, 191, 36)',
              borderWidth: 2,
              hoverBackgroundColor: 'rgba(245, 158, 11, 0.9)',
            },
            {
              label: 'Sum',
              data: data.sum || [],
              backgroundColor: 'rgba(34, 197, 94, 0.7)',
              borderColor: 'rgb(34, 197, 94)',
              borderWidth: 2,
              hoverBackgroundColor: 'rgba(22, 163, 74, 0.9)',
            }
          ]
        };

      case 'multi_bar':
        return {
          labels: data.people?.labels || [],
          datasets: [
            {
              label: 'People',
              data: data.people?.values || [],
              backgroundColor: 'rgba(59, 130, 246, 0.7)',
              borderColor: 'rgb(59, 130, 246)',
              borderWidth: 2,
              hoverBackgroundColor: 'rgba(37, 99, 235, 0.9)',
            },
            {
              label: 'Reviewers',
              data: data.reviewers?.values || [],
              backgroundColor: 'rgba(251, 191, 36, 0.7)',
              borderColor: 'rgb(251, 191, 36)',
              borderWidth: 2,
              hoverBackgroundColor: 'rgba(245, 158, 11, 0.9)',
            },
            {
              label: 'Committers',
              data: data.commiters?.values || [],
              backgroundColor: 'rgba(34, 197, 94, 0.7)',
              borderColor: 'rgb(34, 197, 94)',
              borderWidth: 2,
              hoverBackgroundColor: 'rgba(22, 163, 74, 0.9)',
            },
            {
              label: 'Discussionners',
              data: data.discussionners?.values || [],
              backgroundColor: 'rgba(168, 85, 247, 0.7)',
              borderColor: 'rgb(168, 85, 247)',
              borderWidth: 2,
              hoverBackgroundColor: 'rgba(147, 51, 234, 0.9)',
            }
          ]
        };

      case 'dual_histogram':
        const addValues = data.additions || [];
        const delValues = data.deletions || [];
        
        return {
          labels: Array.from({length: Math.min(addValues.length, 30)}, (_, i) => i + 1),
          datasets: [
            {
              label: 'Additions',
              data: addValues.slice(0, 30),
              backgroundColor: 'rgba(34, 197, 94, 0.7)',
              borderColor: 'rgb(34, 197, 94)',
              borderWidth: 2,
              hoverBackgroundColor: 'rgba(22, 163, 74, 0.9)',
            },
            {
              label: 'Deletions',
              data: delValues.slice(0, 30),
              backgroundColor: 'rgba(239, 68, 68, 0.7)',
              borderColor: 'rgb(239, 68, 68)',
              borderWidth: 2,
              hoverBackgroundColor: 'rgba(220, 38, 38, 0.9)',
            }
          ]
        };

      default:
        return {
          labels: data.labels || [],
          datasets: [{
            label: 'Values',
            data: data.values || [],
            backgroundColor: 'rgba(59, 130, 246, 0.7)',
            borderColor: 'rgb(59, 130, 246)',
            borderWidth: 2,
            hoverBackgroundColor: 'rgba(37, 99, 235, 0.9)',
          }]
        };
    }
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          font: {
            size: 13,
            weight: '500'
          },
          padding: 15,
          usePointStyle: true,
          pointStyle: 'circle',
        }
      },
      title: {
        display: !!data.title,
        text: data.title || '',
        font: {
          size: 18,
          weight: 'bold'
        },
        padding: {
          top: 10,
          bottom: 20
        }
      },
      tooltip: {
        enabled: true,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        displayColors: true,
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += typeof context.parsed.y === 'number' 
                ? context.parsed.y.toFixed(2) 
                : context.parsed.y;
            }
            return label;
          }
        }
      }
    },
    scales: data.type !== 'pie' && data.type !== 'scatter' ? {
      x: {
        title: {
          display: !!data.xLabel,
          text: data.xLabel || '',
          font: {
            size: 13,
            weight: 'bold'
          },
          padding: { top: 10 }
        },
        ticks: {
          font: {
            size: 11
          },
          maxRotation: 45,
          minRotation: 0,
          autoSkip: true,
          maxTicksLimit: 20
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.05)',
        }
      },
      y: {
        title: {
          display: !!data.yLabel,
          text: data.yLabel || '',
          font: {
            size: 13,
            weight: 'bold'
          },
          padding: { bottom: 10 }
        },
        ticks: {
          font: {
            size: 11
          },
          callback: function(value) {
            if (Math.abs(value) >= 1000) {
              return (value / 1000).toFixed(1) + 'k';
            }
            return value;
          }
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.05)',
        },
        beginAtZero: true
      }
    } : data.type === 'scatter' ? {
      x: {
        type: 'linear',
        position: 'bottom',
        title: {
          display: !!data.xLabel,
          text: data.xLabel || 'X',
          font: {
            size: 13,
            weight: 'bold'
          }
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.05)',
        }
      },
      y: {
        title: {
          display: !!data.yLabel,
          text: data.yLabel || 'Y',
          font: {
            size: 13,
            weight: 'bold'
          }
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.05)',
        }
      }
    } : undefined,
    indexAxis: data.type === 'horizontal_bar' ? 'y' : 'x',
    animation: {
      duration: 750,
      easing: 'easeInOutQuart'
    }
  };

  const renderChart = () => {
    const chartData = prepareChartData();

    switch (data.type) {
      case 'line':
        return <Line ref={chartRef} data={chartData} options={chartOptions} />;
      case 'bar':
      case 'horizontal_bar':
      case 'grouped_bar':
      case 'histogram':
      case 'dual_histogram':
      case 'multi_bar':
        return <Bar ref={chartRef} data={chartData} options={chartOptions} />;
      case 'pie':
        return <Pie ref={chartRef} data={chartData} options={chartOptions} />;
      case 'scatter':
      case 'scatter_multi':
        return <Scatter ref={chartRef} data={chartData} options={chartOptions} />;
      default:
        return <Bar ref={chartRef} data={chartData} options={chartOptions} />;
    }
  };

  return (
    <div className="w-full h-full min-h-[300px]">
      {renderChart()}
    </div>
  );
};

export default InteractiveChart;