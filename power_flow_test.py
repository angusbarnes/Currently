import pandapower as pp

net = pp.create_empty_network() 

slack_bus = pp.create_bus(net, vn_kv=20.)
b2 = pp.create_bus(net, vn_kv=20.)
b3 = pp.create_bus(net, vn_kv=20.)


pp.create_line(net, from_bus=slack_bus, to_bus=b2, length_km=2.5, std_type="NAYY 4x50 SE")
pp.create_line(net, from_bus=slack_bus, to_bus=b3, length_km=2.5, std_type="NAYY 4x50 SE")      
pp.create_ext_grid(net, bus=slack_bus)


pp.create_load(net, bus=b2, p_mw=1.5, q_mvar=0.5)
pp.create_load(net, bus=b3, p_mw=1.0)




pp.runpp(net)

print(net.res_bus.vm_pu)
print(net.res_bus)
print(net.res_line.loading_percent)
