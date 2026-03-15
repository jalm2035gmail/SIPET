import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import {
  DollarSign,
  TrendingUp,
  CreditCard,
  Download,
  Calendar,
  BarChart3,
  Wallet,
  Clock
} from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const CommissionDashboard = () => {
  const [balance, setBalance] = useState(null);
  const [payouts, setPayouts] = useState([]);
  const [stats, setStats] = useState({});
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawMethod, setWithdrawMethod] = useState('paypal');

  useEffect(() => {
    fetchCommissionData();
  }, []);

  const fetchCommissionData = async () => {
    setLoading(true);
    try {
      const [balanceRes, payoutsRes, statsRes] = await Promise.all([
        axios.get('/api/commissions/vendor/balance'),
        axios.get('/api/commissions/vendor/payouts?limit=5'),
        axios.get('/api/vendor/dashboard/stats')
      ]);

      setBalance(balanceRes.data);
      setPayouts(payoutsRes.data.payouts);
      setStats(statsRes.data);
      generateChartData(payoutsRes.data.payouts);
    } catch (error) {
      console.error('Error fetching commission data:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateChartData = (payoutsData) => {
    const last6Months = [];
    for (let i = 5; i >= 0; i--) {
      const date = new Date();
      date.setMonth(date.getMonth() - i);
      const month = date.toLocaleString('default', { month: 'short' });
      
      const monthPayout = payoutsData.find(p => {
        const payoutDate = new Date(p.period.start);
        return payoutDate.getMonth() === date.getMonth() && 
               payoutDate.getFullYear() === date.getFullYear();
      });

      last6Months.push({
        month,
        earnings: monthPayout ? monthPayout.net_amount : 0,
        commission: monthPayout ? monthPayout.total_commission : 0,
        sales: monthPayout ? monthPayout.total_sales : 0
      });
    }

    setChartData(last6Months);
  };

  const handleWithdraw = async () => {
    if (!withdrawAmount || parseFloat(withdrawAmount) <= 0) {
      alert('Please enter a valid amount');
      return;
    }

    if (parseFloat(withdrawAmount) > balance.available_balance) {
      alert(`Maximum withdrawable amount: $${balance.available_balance}`);
      return;
    }

    if (!confirm(`Withdraw $${withdrawAmount} to your ${withdrawMethod} account?`)) {
      return;
    }

    try {
      const response = await axios.post('/api/commissions/vendor/withdraw', {
        amount: parseFloat(withdrawAmount),
        payment_method: withdrawMethod,
        payment_details: {
          paypal_email: 'vendor@example.com' // En realidad sería del perfil
        }
      });

      alert('Withdrawal request submitted successfully!');
      setWithdrawAmount('');
      fetchCommissionData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error submitting withdrawal request');
    }
  };

  const downloadStatement = async (payoutId, format = 'pdf') => {
    try {
      const response = await axios.get(`/api/commissions/payouts/${payoutId}/statement?format=${format}`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `statement-${payoutId}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading statement:', error);
    }
  };

  if (loading) {
    return <div>Loading commission data...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Earnings & Payouts</h1>
        <p className="text-gray-600">Manage your earnings and withdrawal requests</p>
      </div>

      {/* Balance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600">Available Balance</p>
              <p className="text-3xl font-bold">${balance?.available_balance?.toFixed(2)}</p>
              <p className="text-sm text-gray-500">Ready for withdrawal</p>
            </div>
            <div className="p-3 bg-green-100 rounded-full">
              <Wallet className="h-6 w-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600">Pending Balance</p>
              <p className="text-3xl font-bold">${balance?.pending_balance?.toFixed(2)}</p>
              <p className="text-sm text-gray-500">In completed orders</p>
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <Clock className="h-6 w-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600">Total Commission</p>
              <p className="text-3xl font-bold">${stats?.total_commission?.toFixed(2)}</p>
              <p className="text-sm text-gray-500">This month</p>
            </div>
            <div className="p-3 bg-purple-100 rounded-full">
              <DollarSign className="h-6 w-6 text-purple-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Withdrawal Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Withdraw Funds</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Amount</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 transform -translate-y-1/2">$</span>
              <input
                type="number"
                value={withdrawAmount}
                onChange={(e) => setWithdrawAmount(e.target.value)}
                className="w-full pl-8 pr-4 py-2 border rounded-lg"
                placeholder="0.00"
                max={balance?.available_balance}
                min="10"
              />
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Max: ${balance?.available_balance?.toFixed(2)}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Payment Method</label>
            <select
              value={withdrawMethod}
              onChange={(e) => setWithdrawMethod(e.target.value)}
              className="w-full py-2 border rounded-lg"
            >
              <option value="paypal">PayPal</option>
              <option value="bank_transfer">Bank Transfer</option>
              <option value="stripe_connect">Stripe Connect</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleWithdraw}
              disabled={!withdrawAmount || parseFloat(withdrawAmount) < 10}
              className="w-full py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Request Withdrawal
            </button>
          </div>
        </div>
      </div>

      {/* Earnings Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold">Earnings Overview</h2>
          <select className="p-2 border rounded-lg">
            <option>Last 6 Months</option>
            <option>Last 12 Months</option>
            <option>This Year</option>
            <option>Last Year</option>
          </select>
        </div>

        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip 
                formatter={(value) => [`$${value.toFixed(2)}`, 'Amount']}
                labelFormatter={(label) => `Month: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="earnings" 
                stroke="#10b981" 
                strokeWidth={2}
                name="Earnings"
              />
              <Line 
                type="monotone" 
                dataKey="sales" 
                stroke="#3b82f6" 
                strokeWidth={2}
                name="Sales"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Payouts */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold">Recent Payouts</h2>
          <button className="flex items-center gap-2 text-blue-600 hover:text-blue-800">
            <Download className="h-4 w-4" />
            Export All
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3">Reference</th>
                <th className="text-left py-3">Period</th>
                <th className="text-left py-3">Total Sales</th>
                <th className="text-left py-3">Commission</th>
                <th className="text-left py-3">Net Amount</th>
                <th className="text-left py-3">Status</th>
                <th className="text-left py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {payouts.map(payout => (
                <tr key={payout.id} className="border-b hover:bg-gray-50">
                  <td className="py-3">
                    <div className="font-mono text-sm">{payout.reference_number}</div>
                  </td>
                  <td className="py-3">
                    <div className="text-sm">
                      {new Date(payout.period.start).toLocaleDateString()} - 
                      {new Date(payout.period.end).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="py-3 font-semibold">
                    ${payout.total_sales.toFixed(2)}
                  </td>
                  <td className="py-3 text-red-600">
                    -${payout.total_commission.toFixed(2)}
                  </td>
                  <td className="py-3 font-bold text-green-600">
                    ${payout.net_amount.toFixed(2)}
                  </td>
                  <td className="py-3">
                    <span className={`px-3 py-1 rounded-full text-sm ${
                      payout.status === 'paid' 
                        ? 'bg-green-100 text-green-800'
                        : payout.status === 'processing'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {payout.status}
                    </span>
                  </td>
                  <td className="py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => downloadStatement(payout.id, 'pdf')}
                        className="p-2 text-gray-600 hover:text-blue-600"
                        title="Download Statement"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      {payout.invoice_url && (
                        <a
                          href={payout.invoice_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 text-gray-600 hover:text-green-600"
                          title="View Invoice"
                        >
                          <CreditCard className="h-4 w-4" />
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {payouts.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <CreditCard className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p>No payout history yet</p>
          </div>
        )}
      </div>

      {/* Commission Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Commission Settings</h2>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <h3 className="font-semibold">Current Commission Rate</h3>
              <p className="text-sm text-gray-600">
                {stats.commission_rate || 10}% per sale
              </p>
            </div>
            <button className="px-4 py-2 border rounded-lg hover:bg-gray-50">
              View Plan Details
            </button>
          </div>

          <div className="p-4 border rounded-lg bg-blue-50">
            <div className="flex items-start gap-3">
              <BarChart3 className="h-5 w-5 text-blue-600 mt-0.5" />
              <div>
                <h3 className="font-semibold">Commission Breakdown</h3>
                <p className="text-sm text-gray-600">
                  Your current plan includes commission rates based on product categories
                </p>
              </div>
            </div>
            
            <div className="mt-4 space-y-2">
              {stats.category_rates?.map((category, index) => (
                <div key={index} className="flex justify-between items-center">
                  <span>{category.name}</span>
                  <span className="font-semibold">{category.rate}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommissionDashboard;
