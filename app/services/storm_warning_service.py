"""
Storm Warning Service
Handles NOAA storm warnings and severe weather alerts
"""

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import os
import warnings
warnings.filterwarnings('ignore')

class StormWarningService:
    """Service for fetching and processing NOAA storm warnings."""

    def __init__(self):
        """Initialize storm warning service."""
        self.noaa_api_key = os.environ.get('NOAA_API_KEY')
        self.base_urls = {
        'alerts': 'https://api.weather.gov/alerts',
        'cap': 'https://alerts.weather.gov/cap',
        'nws': 'https://api.weather.gov'
        }
        self.alert_types = {
        'TORNADO_WARNING': {'severity': 'EXTREME', 'impact': 'HIGH', 'color': '#dc3545'},
        'TORNADO_WATCH': {'severity': 'SEVERE', 'impact': 'HIGH', 'color': '#fd7e14'},
        'SEVERE_THUNDERSTORM_WARNING': {'severity': 'SEVERE', 'impact': 'MEDIUM', 'color': '#ffc107'},
        'SEVERE_THUNDERSTORM_WATCH': {'severity': 'MODERATE', 'impact': 'MEDIUM', 'color': '#20c997'},
        'FLOOD_WARNING': {'severity': 'SEVERE', 'impact': 'HIGH', 'color': '#6f42c1'},
        'FLOOD_WATCH': {'severity': 'MODERATE', 'impact': 'MEDIUM', 'color': '#17a2b8'},
        'WINTER_STORM_WARNING': {'severity': 'SEVERE', 'impact': 'HIGH', 'color': '#6c757d'},
        'WINTER_STORM_WATCH': {'severity': 'MODERATE', 'impact': 'MEDIUM', 'color': '#adb5bd'},
        'HEAT_WARNING': {'severity': 'SEVERE', 'impact': 'HIGH', 'color': '#e83e8c'},
        'HEAT_WATCH': {'severity': 'MODERATE', 'impact': 'MEDIUM', 'color': '#fd7e14'},
        'HIGH_WIND_WARNING': {'severity': 'SEVERE', 'impact': 'MEDIUM', 'color': '#20c997'},
        'WIND_ADVISORY': {'severity': 'MODERATE', 'impact': 'LOW', 'color': '#6c757d'}
        }

    def get_active_alerts(self, latitude: float, longitude: float, radius_miles: int = 50) -> List[Dict[str, Any]]:
        """
        Get active storm warnings for a specific location.

        Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        radius_miles: Search radius in miles

        Returns:
        List of active alerts
        """
        try:
            if not self.noaa_api_key:
                print(" NOAA API key not found, using mock storm warnings")
                return self._generate_mock_alerts(latitude, longitude)

                # Get alerts from NOAA API
                alerts = self._fetch_noaa_alerts(latitude, longitude, radius_miles)

                if not alerts:
                    print(" No storm warnings available, using mock data")
                    return self._generate_mock_alerts(latitude, longitude)

                    return alerts

        except Exception as e:
            print(f" Error fetching storm warnings: {e}")
            return self._generate_mock_alerts(latitude, longitude)

    def get_alert_summary(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary of active alerts.

        Args:
        alerts: List of alert dictionaries

        Returns:
        Summary dictionary
        """
        if not alerts:
            return {
            'total_alerts': 0,
            'severity_levels': {},
            'alert_types': {},
            'highest_severity': 'NONE',
            'impact_assessment': 'NONE'
            }

            severity_counts = {}
            type_counts = {}
            severities = []

            for alert in alerts:
                alert_type = alert.get('event', 'UNKNOWN')
                severity = alert.get('severity', 'UNKNOWN')

                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
                severities.append(severity)

                # Determine highest severity
                severity_order = ['EXTREME', 'SEVERE', 'MODERATE', 'MINOR', 'UNKNOWN']
                highest_severity = 'NONE'
                for severity in severity_order:
                    if severity in severity_counts:
                        highest_severity = severity
                        break

                        # Assess overall impact
                        impact_assessment = self._assess_impact(severity_counts, type_counts)

                        return {
                        'total_alerts': len(alerts),
                        'severity_levels': severity_counts,
                        'alert_types': type_counts,
                        'highest_severity': highest_severity,
                        'impact_assessment': impact_assessment,
                        'last_updated': datetime.now().isoformat()
                        }

    def calculate_demand_impact(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate potential impact on electricity demand.

        Args:
        alerts: List of active alerts

        Returns:
        Demand impact assessment
        """
        if not alerts:
            return {
            'demand_impact': 'NONE',
            'impact_factor': 1.0,
            'confidence': 'HIGH',
            'reasoning': 'No active weather alerts'
            }

            impact_factors = []
            impact_reasons = []

            for alert in alerts:
                alert_type = alert.get('event', 'UNKNOWN')
                severity = alert.get('severity', 'UNKNOWN')

                # Calculate impact factor based on alert type and severity
                base_impact = self._get_base_impact_factor(alert_type)
                severity_multiplier = self._get_severity_multiplier(severity)
                impact_factor = base_impact * severity_multiplier

                impact_factors.append(impact_factor)
                impact_reasons.append(f"{alert_type} ({severity}): {impact_factor:.2f}x")

                # Calculate overall impact
                max_impact = max(impact_factors) if impact_factors else 1.0
                avg_impact = sum(impact_factors) / len(impact_factors) if impact_factors else 1.0

                # Determine demand impact level
                if max_impact >= 1.5:
                    demand_impact = 'HIGH'
                    confidence = 'HIGH'
        elif max_impact >= 1.2:
            demand_impact = 'MEDIUM'
            confidence = 'MEDIUM'
        elif max_impact >= 1.05:
            demand_impact = 'LOW'
            confidence = 'MEDIUM'
        else:
            demand_impact = 'MINIMAL'
            confidence = 'HIGH'

            return {
            'demand_impact': demand_impact,
            'impact_factor': max_impact,
            'confidence': confidence,
            'reasoning': '; '.join(impact_reasons),
            'alert_count': len(alerts),
            'max_impact_factor': max_impact,
            'avg_impact_factor': avg_impact
            }

    def _fetch_noaa_alerts(self, latitude: float, longitude: float, radius_miles: int) -> List[Dict[str, Any]]:
        """Fetch alerts from NOAA API."""
        try:
            # This would make actual API calls to NOAA
            # For now, return mock data
            return self._generate_mock_alerts(latitude, longitude)
        except Exception as e:
            print(f"Error fetching NOAA alerts: {e}")
            return []

    def _generate_mock_alerts(self, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """Generate mock storm warnings for development."""
        import random

        # Generate realistic mock alerts based on location
        mock_alerts = []

        # Simulate different alert types based on location
        if latitude > 40: # Northern states - winter storms
            if random.random() < 0.3:
                mock_alerts.append({
                'id': f'WINTER_STORM_{random.randint(1000, 9999)}',
                'event': 'WINTER_STORM_WARNING',
                'severity': 'SEVERE',
                'headline': 'Winter Storm Warning',
                'description': 'Heavy snow and strong winds expected. Power outages possible.',
                'effective': (datetime.now() - timedelta(hours=2)).isoformat(),
                'expires': (datetime.now() + timedelta(hours=12)).isoformat(),
                'area': f'{latitude:.2f}, {longitude:.2f}',
                'urgency': 'IMMEDIATE',
                'certainty': 'LIKELY'
                })

                if latitude < 35: # Southern states - severe thunderstorms
                    if random.random() < 0.4:
                        mock_alerts.append({
                        'id': f'SEVERE_THUNDERSTORM_{random.randint(1000, 9999)}',
                        'event': 'SEVERE_THUNDERSTORM_WARNING',
                        'severity': 'SEVERE',
                        'headline': 'Severe Thunderstorm Warning',
                        'description': 'Damaging winds and large hail possible. Power outages likely.',
                        'effective': (datetime.now() - timedelta(minutes=30)).isoformat(),
                        'expires': (datetime.now() + timedelta(hours=2)).isoformat(),
                        'area': f'{latitude:.2f}, {longitude:.2f}',
                        'urgency': 'IMMEDIATE',
                        'certainty': 'LIKELY'
                        })

                        # Random tornado watch (rare)
                        if random.random() < 0.1:
                            mock_alerts.append({
                            'id': f'TORNADO_WATCH_{random.randint(1000, 9999)}',
                            'event': 'TORNADO_WATCH',
                            'severity': 'SEVERE',
                            'headline': 'Tornado Watch',
                            'description': 'Conditions favorable for tornado development. Monitor weather closely.',
                            'effective': (datetime.now() - timedelta(hours=1)).isoformat(),
                            'expires': (datetime.now() + timedelta(hours=6)).isoformat(),
                            'area': f'{latitude:.2f}, {longitude:.2f}',
                            'urgency': 'EXPECTED',
                            'certainty': 'POSSIBLE'
                            })

                            # Heat warning in summer months
                            if datetime.now().month in [6, 7, 8] and random.random() < 0.2:
                                mock_alerts.append({
                                'id': f'HEAT_WARNING_{random.randint(1000, 9999)}',
                                'event': 'HEAT_WARNING',
                                'severity': 'SEVERE',
                                'headline': 'Excessive Heat Warning',
                                'description': 'Dangerous heat conditions. Increased cooling demand expected.',
                                'effective': (datetime.now() - timedelta(hours=4)).isoformat(),
                                'expires': (datetime.now() + timedelta(hours=24)).isoformat(),
                                'area': f'{latitude:.2f}, {longitude:.2f}',
                                'urgency': 'IMMEDIATE',
                                'certainty': 'LIKELY'
                                })

                                return mock_alerts

    def _assess_impact(self, severity_counts: Dict[str, int], type_counts: Dict[str, int]) -> str:
        """Assess overall impact based on alert counts."""
        if 'EXTREME' in severity_counts:
            return 'CRITICAL'
        elif 'SEVERE' in severity_counts and severity_counts['SEVERE'] >= 2:
            return 'HIGH'
        elif 'SEVERE' in severity_counts:
            return 'MODERATE'
        elif 'MODERATE' in severity_counts:
            return 'LOW'
        else:
            return 'MINIMAL'

    def _get_base_impact_factor(self, alert_type: str) -> float:
        """Get base impact factor for alert type."""
        impact_factors = {
        'TORNADO_WARNING': 2.0,
        'TORNADO_WATCH': 1.5,
        'SEVERE_THUNDERSTORM_WARNING': 1.3,
        'SEVERE_THUNDERSTORM_WATCH': 1.1,
        'FLOOD_WARNING': 1.4,
        'FLOOD_WATCH': 1.1,
        'WINTER_STORM_WARNING': 1.6,
        'WINTER_STORM_WATCH': 1.2,
        'HEAT_WARNING': 1.8,
        'HEAT_WATCH': 1.3,
        'HIGH_WIND_WARNING': 1.2,
        'WIND_ADVISORY': 1.05
        }
        return impact_factors.get(alert_type, 1.0)

    def _get_severity_multiplier(self, severity: str) -> float:
        """Get severity multiplier."""
        multipliers = {
        'EXTREME': 1.5,
        'SEVERE': 1.3,
        'MODERATE': 1.1,
        'MINOR': 1.05,
        'UNKNOWN': 1.0
        }
        return multipliers.get(severity, 1.0)

    def get_alert_color(self, alert_type: str) -> str:
        """Get color for alert type."""
        return self.alert_types.get(alert_type, {}).get('color', '#6c757d')

    def get_alert_icon(self, alert_type: str) -> str:
        """Get icon for alert type."""
        icons = {
        'TORNADO_WARNING': '',
        'TORNADO_WATCH': '',
        'SEVERE_THUNDERSTORM_WARNING': '',
        'SEVERE_THUNDERSTORM_WATCH': '',
        'FLOOD_WARNING': '',
        'FLOOD_WATCH': '',
        'WINTER_STORM_WARNING': '',
        'WINTER_STORM_WATCH': '',
        'HEAT_WARNING': '',
        'HEAT_WATCH': '',
        'HIGH_WIND_WARNING': '',
        'WIND_ADVISORY': ''
        }
        return icons.get(alert_type, '')
