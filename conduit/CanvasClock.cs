/// DiaCanvas# sample, based on dia-clock.[ch] from diacanvas2 demos.
/// Copyright (C) 2004  Mario Fuentes <mario@gnome.cl>
///
/// This library is free software; you can redistribute it and/or
/// modify it under the terms of the GNU Lesser General Public
/// License as published by the Free Software Foundation; either
/// version 2.1 of the License, or (at your option) any later version.
///
/// This library is distributed in the hope that it will be useful,
/// but WITHOUT ANY WARRANTY; without even the implied warranty of
/// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
/// Lesser General Public License for more details.
///
/// You should have received a copy of the GNU Lesser General Public
/// License along with this library; if not, write to the Free Software
/// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

using System;
using GLib;
using Dia;

public class CanvasClock : CanvasElement {
	Shape circle, hours, minutes, seconds;
	uint timer;
	int sec = 0;

	protected CanvasClock (IntPtr intptr) : base (intptr) {}

	public CanvasClock ()
	{
		circle = new Shape (ShapeType.Ellipse);
		hours = new Shape (ShapeType.Path);
		minutes = new Shape (ShapeType.Path);
		seconds = new Shape (ShapeType.Path);

		timer = GLib.Timeout.Add (500, new TimeoutHandler (TimeoutFunc));
	}
	
	protected override void Update (double [] affine)
	{
		Point center, p;
		double r, t;

		BaseUpdate (affine);
		center = new Point (Width / 2.0, Height / 2.0);
		r = Math.Min (Width, Height) / 2.0;
			
		circle.Ellipse (center, 2 * r, 2 * r);
		circle.Color = 255;
		ShapeEllipse.SetFill (circle, FillStyle.Solid);
		ShapeEllipse.SetFillColor (circle, 8888888);
		ShapeEllipse.SetLineWidth (circle, 5.0);
		//circle.RequestUpdate ();
		
		t = sec * Math.PI / 21600.0;
		p = new Point (Math.Sin (t) * r * 0.7 + center.X,
				-Math.Cos (t) * r * 0.7 + center.Y);
		hours.Line (center, p);
		ShapePath.SetLineWidth (hours, 5.0);
		hours.RequestUpdate ();

		t = sec * Math.PI / 1800.0;
		p = new Point (Math.Sin (t) * r * 0.85 + center.X,
				-Math.Cos (t) * r * 0.85 + center.Y);
		minutes.Line (center, p);
		ShapePath.SetLineWidth (minutes, 4.0);
		minutes.RequestUpdate ();
			
		t = sec * Math.PI / 30.0;
		p = new Point (Math.Sin (t) * r * 0.9 + center.X,
				-Math.Cos (t) * r * 0.9 + center.Y);
		seconds.Line (center, p);
		seconds.Color = 242424;
		ShapePath.SetLineWidth (seconds, 3.0);
		seconds.RequestUpdate ();
	}

	protected override bool GetShapeIterFunc (ref CanvasIter iter)
	{
		iter.Data[0] = circle.Handle;

		return true;
	}

	protected override bool ShapeNextFunc (ref CanvasIter iter)
	{
		if (iter.Data[0] == circle.Handle)
			iter.Data[0] = hours.Handle;
		else if (iter.Data[0] == hours.Handle)
			iter.Data[0] = minutes.Handle;
		else if (iter.Data[0] == minutes.Handle)
			iter.Data[0] = seconds.Handle;
		else
			iter.Data[0] = IntPtr.Zero;		
		
		return (iter.Data[0] != IntPtr.Zero);
	}

	protected override Shape ShapeValueFunc (ref CanvasIter iter)
	{
		if (iter.Data[0] == IntPtr.Zero)
			return null;
		return new Shape (iter.Data[0]);
	}

	bool TimeoutFunc ()
	{
		DateTime dt = DateTime.Now;
		int lsec = (((dt.Hour * 60) + dt.Minute) * 60) + dt.Second;
		
		if (lsec != sec)
		{
			sec = lsec;
			RequestUpdate ();
		}

		return true;
	}
}
