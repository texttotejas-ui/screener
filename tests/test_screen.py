import unittest,sys
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from screen import analyse,rsi,sma
class ScreenTests(unittest.TestCase):
    def bars(self,descending=False):
        return [[str(date(2024,1,1)+timedelta(days=i)),400-i if descending else 100+i,402-i if descending else 102+i,398-i if descending else 98+i,400-i if descending else 100+i,1000] for i in range(260)]
    def test_trend_gate(self):
        self.assertTrue(analyse(self.bars())['eligible'])
        self.assertFalse(analyse(self.bars(True))['eligible'])
    def test_averages(self): self.assertEqual(sma([1,2,3,4],2),[None,1.5,2.5,3.5])
    def test_flat_rsi(self): self.assertEqual(rsi([100]*50)[-1],50)
    def test_no_false_reversal_in_uptrend(self):
        a=analyse(self.bars()); self.assertEqual(a['scores']['rsi'],0); self.assertEqual(a['scores']['stochastic'],0)
    def test_insufficient_history(self):
        with self.assertRaises(ValueError): analyse(self.bars()[:100])
    def test_bad_data(self):
        b=self.bars(); b[-1][4]=float('nan')
        with self.assertRaises(ValueError): analyse(b)
if __name__=='__main__': unittest.main()
