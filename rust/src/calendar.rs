use std::collections::HashMap;

/// A business calendar supporting O(1) business day arithmetic.
pub struct BusinessCalendar {
    days: Vec<i32>,
    ordinal_to_idx: HashMap<i32, usize>,
}

impl BusinessCalendar {
    pub fn new(ordinals: Vec<i32>) -> Self {
        let mut ordinal_to_idx = HashMap::with_capacity(ordinals.len());
        for (idx, &ord) in ordinals.iter().enumerate() {
            ordinal_to_idx.insert(ord, idx);
        }
        BusinessCalendar {
            days: ordinals,
            ordinal_to_idx,
        }
    }

    pub fn is_business_day(&self, ordinal: i32) -> bool {
        self.days.binary_search(&ordinal).is_ok()
    }

    pub fn add_business_days(&self, ordinal: i32, n: i32) -> Option<i32> {
        let idx = *self.ordinal_to_idx.get(&ordinal)?;
        let target_idx = idx as i32 + n;
        if target_idx < 0 {
            return None;
        }
        self.days.get(target_idx as usize).copied()
    }

    pub fn next_business_day(&self, ordinal: i32) -> Option<i32> {
        match self.days.binary_search(&ordinal) {
            Ok(_) => Some(ordinal),
            Err(idx) => self.days.get(idx).copied(),
        }
    }

    pub fn prev_business_day(&self, ordinal: i32) -> Option<i32> {
        match self.days.binary_search(&ordinal) {
            Ok(_) => Some(ordinal),
            Err(idx) if idx == 0 => None,
            Err(idx) => self.days.get(idx - 1).copied(),
        }
    }

    pub fn business_days_in_range(&self, start: i32, end: i32) -> Vec<i32> {
        let start_idx = self.days.partition_point(|&d| d < start);
        let end_idx = self.days.partition_point(|&d| d <= end);
        self.days[start_idx..end_idx].to_vec()
    }

    pub fn count_business_days(&self, start: i32, end: i32) -> usize {
        let start_idx = self.days.partition_point(|&d| d < start);
        let end_idx = self.days.partition_point(|&d| d <= end);
        end_idx - start_idx
    }

    pub fn get_index(&self, ordinal: i32) -> Option<usize> {
        self.ordinal_to_idx.get(&ordinal).copied()
    }

    pub fn get_at_index(&self, index: usize) -> Option<i32> {
        self.days.get(index).copied()
    }

    pub fn len(&self) -> usize {
        self.days.len()
    }

    pub fn is_empty(&self) -> bool {
        self.days.is_empty()
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
