use std::collections::HashMap;

/// A business calendar supporting O(1) business day arithmetic.
pub struct BusinessCalendar {
    days: Vec<i32>,
    ordinal_to_idx: HashMap<i32, usize>,
}

impl BusinessCalendar {
    pub fn new(ordinals: Vec<i32>) -> Self {
        let n = ordinals.len();
        let mut ordinal_to_idx = HashMap::with_capacity(n);
        let mut i = 0usize;
        while i < n {
            ordinal_to_idx.insert(ordinals[i], i);
            i += 1;
        }
        BusinessCalendar {
            days: ordinals,
            ordinal_to_idx,
        }
    }

    pub fn is_business_day(&self, ordinal: i32) -> bool {
        self.binary_search(ordinal).is_some()
    }

    /// Binary search returning Some(index) if found, None otherwise.
    fn binary_search(&self, target: i32) -> Option<usize> {
        let n = self.days.len();
        if n == 0 {
            return None;
        }
        let mut lo = 0usize;
        let mut hi = n;
        while lo < hi {
            let mid = lo + (hi - lo) / 2;
            if self.days[mid] < target {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
        if lo < n && self.days[lo] == target {
            Some(lo)
        } else {
            None
        }
    }

    /// Lower bound: find first index where days[i] >= target.
    fn lower_bound(&self, target: i32) -> usize {
        let n = self.days.len();
        let mut lo = 0usize;
        let mut hi = n;
        while lo < hi {
            let mid = lo + (hi - lo) / 2;
            if self.days[mid] < target {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
        lo
    }

    /// Upper bound: find first index where days[i] > target.
    fn upper_bound(&self, target: i32) -> usize {
        let n = self.days.len();
        let mut lo = 0usize;
        let mut hi = n;
        while lo < hi {
            let mid = lo + (hi - lo) / 2;
            if self.days[mid] <= target {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
        lo
    }

    pub fn add_business_days(&self, ordinal: i32, n: i32) -> Option<i32> {
        let idx = match self.ordinal_to_idx.get(&ordinal) {
            Some(&i) => i,
            None => return None,
        };
        let target_idx = idx as i32 + n;
        if target_idx < 0 {
            return None;
        }
        let target = target_idx as usize;
        if target < self.days.len() {
            Some(self.days[target])
        } else {
            None
        }
    }

    pub fn next_business_day(&self, ordinal: i32) -> Option<i32> {
        if let Some(_) = self.binary_search(ordinal) {
            return Some(ordinal);
        }
        let idx = self.lower_bound(ordinal);
        if idx < self.days.len() {
            Some(self.days[idx])
        } else {
            None
        }
    }

    pub fn prev_business_day(&self, ordinal: i32) -> Option<i32> {
        if let Some(_) = self.binary_search(ordinal) {
            return Some(ordinal);
        }
        let idx = self.lower_bound(ordinal);
        if idx == 0 {
            None
        } else {
            Some(self.days[idx - 1])
        }
    }

    pub fn business_days_in_range(&self, start: i32, end: i32) -> Vec<i32> {
        let start_idx = self.lower_bound(start);
        let end_idx = self.upper_bound(end);
        let slice_len = end_idx - start_idx;
        let mut result = Vec::with_capacity(slice_len);
        let mut i = start_idx;
        while i < end_idx {
            result.push(self.days[i]);
            i += 1;
        }
        result
    }

    pub fn count_business_days(&self, start: i32, end: i32) -> usize {
        let start_idx = self.lower_bound(start);
        let end_idx = self.upper_bound(end);
        end_idx - start_idx
    }

    pub fn get_index(&self, ordinal: i32) -> Option<usize> {
        match self.ordinal_to_idx.get(&ordinal) {
            Some(&idx) => Some(idx),
            None => None,
        }
    }

    pub fn get_at_index(&self, index: usize) -> Option<i32> {
        if index < self.days.len() {
            Some(self.days[index])
        } else {
            None
        }
    }

    pub fn len(&self) -> usize {
        self.days.len()
    }

    pub fn is_empty(&self) -> bool {
        self.days.len() == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_business_calendar() {
        let ordinals = vec![738886, 738887, 738890, 738891, 738892, 738893, 738894];
        let cal = BusinessCalendar::new(ordinals);

        assert!(cal.is_business_day(738886));
        assert!(!cal.is_business_day(738888));

        assert_eq!(cal.add_business_days(738886, 2), Some(738890));
        assert_eq!(cal.add_business_days(738886, -1), None);

        assert_eq!(cal.next_business_day(738888), Some(738890));
        assert_eq!(cal.prev_business_day(738888), Some(738887));
    }
}
