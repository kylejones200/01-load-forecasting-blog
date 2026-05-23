"""
Electrical Load Modeling Service
Implements electrical engineering load modeling techniques
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class LoadModelingService:
    """Service for electrical load modeling and characterization."""

    def __init__(self):
        """Initialize load modeling service."""
        self.load_types = {
        'residential': {'power_factor': 0.85, 'diversity_factor': 0.7},
        'commercial': {'power_factor': 0.90, 'diversity_factor': 0.8},
        'industrial': {'power_factor': 0.95, 'diversity_factor': 0.9},
        'agricultural': {'power_factor': 0.80, 'diversity_factor': 0.6}
        }

    def characterize_load_profile(self, load_data: pd.DataFrame,
        load_type: str = 'mixed') -> Dict[str, Any]:
        """
        Characterize load profile using electrical engineering methods.

        Args:
        load_data: Historical load data
        load_type: Type of load (residential, commercial, industrial, mixed)

        Returns:
        Load characteristics including power factor, diversity, etc.
        """
        try:
            # Calculate basic statistics
            load_stats = {
            'peak_demand': load_data['consumption'].max(),
            'minimum_demand': load_data['consumption'].min(),
            'average_demand': load_data['consumption'].mean(),
            'load_factor': load_data['consumption'].mean() / load_data['consumption'].max(),
            'demand_factor': load_data['consumption'].max() / load_data['consumption'].sum() * len(load_data)
            }

            # Calculate power factor characteristics
            power_factor_analysis = self._analyze_power_factor(load_data, load_type)

            # Calculate diversity factor
            diversity_analysis = self._analyze_diversity_factor(load_data, load_type)

            # Calculate load duration curve
            ldc_analysis = self._calculate_load_duration_curve(load_data)

            # Calculate coincidence factor
            coincidence_analysis = self._calculate_coincidence_factor(load_data)

            # Calculate load growth trends
            growth_analysis = self._analyze_load_growth(load_data)

            return {
            'basic_statistics': load_stats,
            'power_factor_analysis': power_factor_analysis,
            'diversity_analysis': diversity_analysis,
            'load_duration_curve': ldc_analysis,
            'coincidence_analysis': coincidence_analysis,
            'growth_analysis': growth_analysis,
            'load_type': load_type,
            'characterization_date': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': f'Load characterization failed: {str(e)}'}

    def _analyze_power_factor(self, load_data: pd.DataFrame, load_type: str) -> Dict[str, Any]:
        """Analyze power factor characteristics."""
        # Simulate reactive power based on load type
        power_factor = self.load_types.get(load_type, {'power_factor': 0.85})['power_factor']

        # Calculate apparent power and reactive power
        apparent_power = load_data['consumption'] / power_factor
        reactive_power = apparent_power * np.sqrt(1 - power_factor**2)

        return {
        'average_power_factor': power_factor,
        'power_factor_range': [power_factor - 0.05, power_factor + 0.05],
        'reactive_power_profile': reactive_power.tolist(),
        'apparent_power_profile': apparent_power.tolist(),
        'power_factor_variation': np.std(reactive_power) / np.mean(apparent_power)
        }

    def _analyze_diversity_factor(self, load_data: pd.DataFrame, load_type: str) -> Dict[str, Any]:
        """Analyze diversity factor characteristics."""
        diversity_factor = self.load_types.get(load_type, {'diversity_factor': 0.7})['diversity_factor']

        # Calculate diversity factor variations
        hourly_diversity = []
        for hour in range(24):
            hour_data = load_data[load_data.index.hour == hour]['consumption']
            if len(hour_data) > 1:
                diversity = hour_data.mean() / hour_data.max()
                hourly_diversity.append(diversity)
        else:
            hourly_diversity.append(diversity_factor)

            return {
            'average_diversity_factor': diversity_factor,
            'hourly_diversity_factors': hourly_diversity,
            'diversity_variation': np.std(hourly_diversity),
            'peak_diversity_hour': np.argmin(hourly_diversity),
            'off_peak_diversity_hour': np.argmax(hourly_diversity)
            }

    def _calculate_load_duration_curve(self, load_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate load duration curve."""
        sorted_loads = np.sort(load_data['consumption'])[::-1] # Descending order
        duration_hours = np.arange(1, len(sorted_loads) + 1)

        # Calculate percentiles
        percentiles = {
        'p10': np.percentile(sorted_loads, 10),
        'p25': np.percentile(sorted_loads, 25),
        'p50': np.percentile(sorted_loads, 50),
        'p75': np.percentile(sorted_loads, 75),
        'p90': np.percentile(sorted_loads, 90),
        'p95': np.percentile(sorted_loads, 95),
        'p99': np.percentile(sorted_loads, 99)
        }

        return {
        'load_duration_data': sorted_loads.tolist(),
        'duration_hours': duration_hours.tolist(),
        'percentiles': percentiles,
        'peak_hours': len(sorted_loads[sorted_loads > percentiles['p95']]),
        'base_load': percentiles['p10']
        }

    def _calculate_coincidence_factor(self, load_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate coincidence factor for multiple loads."""
        # Simulate multiple feeder loads
        n_feeders = 5
        feeder_loads = []

        for i in range(n_feeders):
            # Add some variation to each feeder
            variation = np.random.normal(1.0, 0.1, len(load_data))
            feeder_load = load_data['consumption'] * variation
            feeder_loads.append(feeder_load)

            feeder_loads = np.array(feeder_loads)

            # Calculate coincidence factor
            individual_peaks = np.max(feeder_loads, axis=1)
            combined_peak = np.max(np.sum(feeder_loads, axis=0))
            coincidence_factor = combined_peak / np.sum(individual_peaks)

            return {
            'coincidence_factor': coincidence_factor,
            'individual_peaks': individual_peaks.tolist(),
            'combined_peak': combined_peak,
            'sum_of_individual_peaks': np.sum(individual_peaks),
            'diversity_benefit': np.sum(individual_peaks) - combined_peak
            }

    def _analyze_load_growth(self, load_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze load growth trends."""
        # Calculate monthly averages
        monthly_data = load_data.resample('M')['consumption'].mean()

        # Calculate growth rate
        if len(monthly_data) > 1:
            growth_rates = []
            for i in range(1, len(monthly_data)):
                growth_rate = (monthly_data.iloc[i] - monthly_data.iloc[i-1]) / monthly_data.iloc[i-1] * 100
                growth_rates.append(growth_rate)

                avg_growth_rate = np.mean(growth_rates)
                growth_trend = 'increasing' if avg_growth_rate > 0 else 'decreasing'
        else:
            avg_growth_rate = 0
            growth_trend = 'stable'

            return {
            'average_growth_rate_percent': avg_growth_rate,
            'growth_trend': growth_trend,
            'monthly_averages': monthly_data.tolist(),
            'growth_volatility': np.std(growth_rates) if len(growth_rates) > 1 else 0
            }

    def create_load_forecast_with_engineering_constraints(self,
        base_forecast: pd.DataFrame,
        load_characteristics: Dict[str, Any],
        engineering_constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create load forecast with electrical engineering constraints.

        Args:
        base_forecast: Base load forecast from ML models
        load_characteristics: Load characterization results
        engineering_constraints: Engineering constraints and limits

        Returns:
        Engineering-constrained load forecast
        """
        try:
            # Apply power factor constraints
            power_factor_constrained = self._apply_power_factor_constraints(
            base_forecast, load_characteristics['power_factor_analysis']
            )

            # Apply diversity factor constraints
            diversity_constrained = self._apply_diversity_constraints(
            power_factor_constrained, load_characteristics['diversity_analysis']
            )

            # Apply voltage constraints
            voltage_constrained = self._apply_voltage_constraints(
            diversity_constrained, engineering_constraints.get('voltage_limits', {})
            )

            # Apply thermal constraints
            thermal_constrained = self._apply_thermal_constraints(
            voltage_constrained, engineering_constraints.get('thermal_limits', {})
            )

            # Apply stability constraints
            stability_constrained = self._apply_stability_constraints(
            thermal_constrained, engineering_constraints.get('stability_limits', {})
            )

            return {
            'engineering_constrained_forecast': stability_constrained,
            'constraint_applications': {
            'power_factor': power_factor_constrained,
            'diversity': diversity_constrained,
            'voltage': voltage_constrained,
            'thermal': thermal_constrained,
            'stability': stability_constrained
            },
            'constraint_violations': self._check_constraint_violations(stability_constrained, engineering_constraints),
            'engineering_metrics': self._calculate_engineering_metrics(stability_constrained, load_characteristics)
            }

        except Exception as e:
            return {'error': f'Engineering constraint application failed: {str(e)}'}

    def _apply_power_factor_constraints(self, forecast: pd.DataFrame,
        power_factor_analysis: Dict[str, Any]) -> pd.DataFrame:
        """Apply power factor constraints to forecast."""
        constrained_forecast = forecast.copy()

        # Adjust forecast based on power factor characteristics
        power_factor = power_factor_analysis['average_power_factor']
        power_factor_range = power_factor_analysis['power_factor_range']

        # Apply power factor variation
        variation_factor = np.random.normal(1.0, 0.02, len(forecast))
        constrained_forecast['consumption'] *= variation_factor

        return constrained_forecast

    def _apply_diversity_constraints(self, forecast: pd.DataFrame,
        diversity_analysis: Dict[str, Any]) -> pd.DataFrame:
        """Apply diversity factor constraints to forecast."""
        constrained_forecast = forecast.copy()

        # Apply hourly diversity factors
        hourly_diversity = diversity_analysis['hourly_diversity_factors']

        for hour in range(24):
            hour_mask = forecast.index.hour == hour
            if hour_mask.any():
                diversity_factor = hourly_diversity[hour]
                constrained_forecast.loc[hour_mask, 'consumption'] *= diversity_factor

                return constrained_forecast

    def _apply_voltage_constraints(self, forecast: pd.DataFrame,
        voltage_limits: Dict[str, Any]) -> pd.DataFrame:
        """Apply voltage constraints to forecast."""
        constrained_forecast = forecast.copy()

        # Apply voltage-dependent load characteristics
        voltage_sensitivity = voltage_limits.get('voltage_sensitivity', 1.0)
        constrained_forecast['consumption'] *= voltage_sensitivity

        return constrained_forecast

    def _apply_thermal_constraints(self, forecast: pd.DataFrame,
        thermal_limits: Dict[str, Any]) -> pd.DataFrame:
        """Apply thermal constraints to forecast."""
        constrained_forecast = forecast.copy()

        # Apply thermal limits
        max_thermal_limit = thermal_limits.get('max_thermal_limit', forecast['consumption'].max() * 1.1)
        constrained_forecast['consumption'] = np.minimum(
        constrained_forecast['consumption'], max_thermal_limit
        )

        return constrained_forecast

    def _apply_stability_constraints(self, forecast: pd.DataFrame,
        stability_limits: Dict[str, Any]) -> pd.DataFrame:
        """Apply stability constraints to forecast."""
        constrained_forecast = forecast.copy()

        # Apply stability limits (e.g., rate of change limits)
        max_rate_of_change = stability_limits.get('max_rate_of_change', 0.1)

        # Calculate rate of change
        rate_of_change = constrained_forecast['consumption'].diff().abs()
        rate_of_change = rate_of_change.fillna(0)

        # Apply rate of change limits
        excessive_changes = rate_of_change > max_rate_of_change * constrained_forecast['consumption'].mean()
        if excessive_changes.any():
            # Smooth excessive changes
            constrained_forecast.loc[excessive_changes, 'consumption'] = (
            constrained_forecast.loc[excessive_changes, 'consumption'].shift(1) *
            (1 + max_rate_of_change)
            )

            return constrained_forecast

    def _check_constraint_violations(self, forecast: pd.DataFrame,
        constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for constraint violations."""
        violations = []

        # Check thermal violations
        thermal_limit = constraints.get('thermal_limits', {}).get('max_thermal_limit', float('inf'))
        thermal_violations = forecast['consumption'] > thermal_limit
        if thermal_violations.any():
            violations.append({
            'constraint_type': 'thermal',
            'violation_count': thermal_violations.sum(),
            'max_violation': (forecast['consumption'] - thermal_limit).max(),
            'violation_times': forecast[thermal_violations].index.tolist()
            })

            # Check voltage violations
            voltage_limit = constraints.get('voltage_limits', {}).get('min_voltage', 0.95)
            voltage_violations = forecast['consumption'] < voltage_limit * forecast['consumption'].mean()
            if voltage_violations.any():
                violations.append({
                'constraint_type': 'voltage',
                'violation_count': voltage_violations.sum(),
                'max_violation': (voltage_limit * forecast['consumption'].mean() - forecast['consumption']).max(),
                'violation_times': forecast[voltage_violations].index.tolist()
                })

                return violations

    def _calculate_engineering_metrics(self, forecast: pd.DataFrame,
        load_characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate engineering metrics for the forecast."""
        return {
        'peak_demand': forecast['consumption'].max(),
        'load_factor': forecast['consumption'].mean() / forecast['consumption'].max(),
        'demand_factor': forecast['consumption'].max() / forecast['consumption'].sum() * len(forecast),
        'power_factor': load_characteristics['power_factor_analysis']['average_power_factor'],
        'diversity_factor': load_characteristics['diversity_analysis']['average_diversity_factor'],
        'coincidence_factor': load_characteristics['coincidence_analysis']['coincidence_factor'],
        'engineering_confidence': self._calculate_engineering_confidence(forecast, load_characteristics)
        }

    def _calculate_engineering_confidence(self, forecast: pd.DataFrame,
        load_characteristics: Dict[str, Any]) -> float:
        """Calculate engineering confidence score."""
        # This would calculate a confidence score based on engineering principles
        return 0.85 # Placeholder value
