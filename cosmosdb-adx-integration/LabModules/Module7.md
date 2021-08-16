## Explore, Analyze and Visualize data in near real-time using ADX 
In this module you will learn about how easy it is to explore, analyze and visualize data using ADX. You will also learn how to build a near real-time dashboard with few sample queries using ADX Dashboards. ADX Dashboards is a feature of ADX which can be accessed from ADX Web UI. You can also use other visualization tools like Power BI or Grafana depending on your requirements. 
I am using ADX dashboards due to following reasons -
   - Easy to use with ADX as source
   - Leverage data exploration KQL(Kusto Query Language) queries as it is to build dashboards
   - Highly performant so you can build near real time dashboards with raw or aggregated data
   - Free to use so no additional cost

### Let us get started
1. Open [ADX Web UI](https://dataexplorer.azure.com/) to connect to the ADX cluster, details on using Web UI are given [here](https://docs.microsoft.com/en-us/azure/data-explorer/web-query-data)<br/>
You can also use Kusto explorer which is a desktop edition similar to the Web UI, details are given [here](https://docs.microsoft.com/en-us/azure/data-explorer/kusto/tools/kusto-explorer)
2. Add ADX cluster that we built in Module 5 on Web UI.
3. Sample KQL queries 
   - This query will select top 5 records in descending order by Timestamp 
     ```
     TransformedNrtaLabTable
     | take 5 
     | order by Timestamp desc  
     ```
     You can also write queries using T-SQL e.g. above query is same as following T-SQL query -
     ```
     select top(5) * from TransformedNrtaLabTable order by Timestamp desc
     ```
     
   - Aggregations on fly work at a lightning speed in ADX e.g. 
     ```
      TransformedNrtaLabTable 
      | where Action == 'Purchased'
      | summarize TotalSales = count() by Category
      | render piechart 
     ```
     
    - Aggregate price by 5mins resolution for each brand
      ```
      TransformedNrtaLabTable
      | summarize TotalPrice=sum(Price) by bin(Timestamp,5m), Brand
      | render timechart  
      ```
### Glimpse of advanced native features like time series analysis and forecasting 
- This query forecasts the next week sales using time series decomposition on historical data
    ```
      //Forecasting next week sales 
      let starttime = datetime(2021-08-08);
      let dt = 2h;
      let horizon=7d;
      TransformedNrtaLabTable
      | where Action == "Purchased"
      | make-series cnt=count() on Timestamp from starttime to now()+horizon step dt by Brand
      | extend forecast = series_decompose_forecast(cnt, toint(horizon/dt), tolong(24h/dt))
      | render timechart 
    ```

  
  ### Build a dashboard using ADX Dashboards with above mentioned queries
  1. Click on 'Share' option on right menu of ADX Web UI, select 'Pin to Dashboard' option
  ![](../images/Dashboard1.png)
  2. Fill in the details and create a new dashboard
  ![](../images/Dashboard2.png)
  3. Click on 'Edit' button on top
  ![](../images/Dashboard3.png)
  4. Then click on 'Add query'
  ![](../images/Dashboard4.png)
  5. Paste any of the KQL queries that were created in Step 3 of 'Sample KQL Queries' above section. Run query and add visuals as needed.
  ![](../images/Dashboard5.png)

  6. Repeat above Step 4 and 5 to add rest of the sample queries on dashboard. You can drag and drop, resize visuals as needed. Finally you will see a dashboard like the one shown below, thats it. So simple and easy!
  ![](../images/Dashboard.png)


