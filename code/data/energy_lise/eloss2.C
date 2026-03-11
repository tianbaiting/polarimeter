#include <iostream>
#include <fstream>


TCanvas *c1 = new TCanvas;


TGraph *gEdEdxLISE(const char* inputFile)
{
  ifstream inFile(inputFile);
  if (!(inFile.is_open())) {                                                        
    cout << "Cannot find input file :" <<inputFile << endl;
    return 0;
  }   
  TGraph *gEdEdx = new TGraph;
  string str;
  for(int i=0;i<3;i++) 
    getline(inFile, str); // skip the first three lines

  // energy: MeV/u, Range: micron - do not depends on A.

  double energy, R[10], dummy;
  int n=0;
  while (getline(inFile,str) ) 
    {
        stringstream ss(str);
        ss  >> energy >> R[0] 
            >> dummy  >> R[1]
            >> dummy  >> R[2] 
            >> dummy  >> R[3] 
            >> dummy  >> R[4]  /* used for calculation */
            >> dummy  >> R[5]; 

        gEdEdx->SetPoint(n++, energy, R[4]);
    }
  inFile.close();
  cout << "Read " << n << " lines of data from the file: " << inputFile << endl;
  cout << "TGraph: x = E(MeV/u), y = dEdx(MeV/um) " << endl;
  return gEdEdx;
}




double eloss(int A, double E0_A, double dx, TGraph *gER, TGraph *gRE)
{
      
    // int A = 12;
    // double dx = 300; // um
    // double E0_A = 200./12; // MeV
    double E0 = E0_A * A; //MeV
    double dE;
    double RE0 = gER->Eval(E0/A,0,"S");

    if(RE0 > dx) {
        double RE1 = RE0 - dx;
        double E1 = gRE->Eval(RE1,0,"S");
        dE = E0 - E1*A;
    }
    else
        dE = E0;
    return dE;
}


void eloss2()
{
    TGraph *gER = gEdEdxLISE("H_c8h8_range.txt");
    TGraph *gRE = new TGraph(gER->GetN(), gER->GetY(), gER->GetX());

    // 定义 E0_A 的范围和步长
    double E0_A_min = 0;
    double E0_A_max = 200;
    double step = 1;

    // 创建向量来存储 E0_A 和对应的 eloss 值
    vector<double> E0_A_values;
    vector<double> eloss_values;
    vector<double> eloss_values2;

    // 计算不同 E0_A 值下的 eloss
    for (double E0_A = E0_A_min; E0_A <= E0_A_max; E0_A += step) {
        double dE = eloss(1, E0_A, 20000, gER, gRE);
        std::cout << "E0_A = " << E0_A << " MeV/u, dE = " << dE << " MeV" << std::endl;
        double E2 = 0;
        E2= E0_A-eloss(1, E0_A, 20000, gER, gRE);
        double dE2 = eloss(1, E2, 20000, gER, gRE);
        std::cout << "E2= " << E2 << " MeV/u, dE = " << dE2 << " MeV" << std::endl;
        E0_A_values.push_back(E0_A);
        eloss_values.push_back(dE);
        eloss_values2.push_back(dE2);
    }

    // 创建 TGraph 对象来绘制图形
    TGraph *graph1 = new TGraph(E0_A_values.size(), &E0_A_values[0], &eloss_values[0]);
    TGraph *graph2 = new TGraph(E0_A_values.size(), &E0_A_values[0], &eloss_values2[0]);

    // 创建画布并绘制图形
    TCanvas *c1 = new TCanvas("c1", "eloss vs E0_A", 800, 600);
    graph1->SetTitle("eloss vs E0;E0;Delta E");
    graph1->SetLineColor(kRed); // 设置第一条线的颜色
    graph1->Draw("AL");

    graph2->SetLineColor(kBlue); // 设置第二条线的颜色
    graph2->Draw("L SAME"); // 在同一个画布上绘制第二条线

        // 创建图例并添加条目
    TLegend *legend = new TLegend(0.7, 0.7, 0.9, 0.9); // 设置图例的位置
    legend->AddEntry(graph1, "1st scintillator", "l");
    legend->AddEntry(graph2, "2nd scintillator", "l");
    legend->Draw();

    // 显示画布
    c1->Draw();
    c1->SaveAs("eloss.png");
}
