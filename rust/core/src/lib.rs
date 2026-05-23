//! SAIDI / SAIFI on flat arrays grouped by a single integer key.

use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq)]
pub struct SaidiSaifiResult {
    pub keys: Vec<i64>,
    pub saidi_min: Vec<f64>,
    pub saifi_events_per_cust: Vec<f64>,
}

/// Aggregate SAIDI (minutes per customer) and SAIFI (interruptions per customer) by key.
pub fn saidi_saifi_by_key(
    group_key: &[i64],
    customers_out: &[f64],
    slot_minutes: &[f64],
    customers_served: &[f64],
) -> SaidiSaifiResult {
    let n = group_key.len();
    assert_eq!(n, customers_out.len());
    assert_eq!(n, slot_minutes.len());
    assert_eq!(n, customers_served.len());

    let mut cust_min: HashMap<i64, f64> = HashMap::new();
    let mut cust_int: HashMap<i64, f64> = HashMap::new();
    let mut cust_served: HashMap<i64, f64> = HashMap::new();

    for i in 0..n {
        let k = group_key[i];
        *cust_min.entry(k).or_default() += customers_out[i] * slot_minutes[i];
        *cust_int.entry(k).or_default() += customers_out[i];
        *cust_served.entry(k).or_default() += customers_served[i];
    }

    let mut keys: Vec<i64> = cust_served.keys().copied().collect();
    keys.sort_unstable();

    let mut saidi_min = Vec::with_capacity(keys.len());
    let mut saifi_events_per_cust = Vec::with_capacity(keys.len());

    for k in &keys {
        let served = cust_served[k];
        let saidi = if served > 0.0 {
            cust_min[k] / served
        } else {
            0.0
        };
        let saifi = if served > 0.0 {
            cust_int[k] / served
        } else {
            0.0
        };
        saidi_min.push(saidi);
        saifi_events_per_cust.push(saifi);
    }

    SaidiSaifiResult {
        keys,
        saidi_min,
        saifi_events_per_cust,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn single_group_metrics() {
        let keys = vec![1, 1, 1];
        let out = vec![10.0, 5.0, 0.0];
        let slot = vec![60.0, 30.0, 15.0];
        let served = vec![1000.0, 1000.0, 1000.0];
        let r = saidi_saifi_by_key(&keys, &out, &slot, &served);
        assert_eq!(r.keys, vec![1]);
        assert!((r.saidi_min[0] - 0.25).abs() < 1e-9);
        assert!((r.saifi_events_per_cust[0] - 15.0 / 3000.0).abs() < 1e-9);
    }
}
