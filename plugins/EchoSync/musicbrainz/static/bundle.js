//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1;
function t() {
	e = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
t();
//#endregion
//#region node_modules/svelte/src/constants.js
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, g = Object.isExtensible, _ = () => {};
function v(e) {
	return e();
}
function y(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function b() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var x = 1024, S = 2048, C = 4096, w = 8192, ee = 16384, te = 32768, ne = 1 << 25, T = 65536, E = 1 << 19, re = 1 << 20, ie = 1 << 25, ae = 1 << 21, oe = 1 << 22, se = 1 << 23, ce = Symbol("$state"), le = Symbol("component"), ue = Symbol("legacy props"), de = Symbol(""), fe = Symbol("attributes"), pe = Symbol("class"), me = Symbol("style"), he = Symbol("text"), ge = Symbol("form reset"), _e = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), ve = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function ye() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function be(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function xe() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var D = !1;
function Se(e) {
	D = e;
}
var O;
function k(e) {
	if (e === null) throw be(), n;
	return O = e;
}
function Ce() {
	return k(/* @__PURE__ */ $t(O));
}
function A(e) {
	if (D) {
		if (/* @__PURE__ */ $t(O) !== null) throw be(), n;
		O = e;
	}
}
function we(e = 1) {
	if (D) {
		for (var t = e, n = O; t--;) n = /* @__PURE__ */ $t(n);
		O = n;
	}
}
function Te(e = !0) {
	for (var t = 0, n = O;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ $t(n);
		e && n.remove(), n = i;
	}
}
function Ee(e) {
	if (!e || e.nodeType !== 8) throw be(), n;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function De(e) {
	return e === this.v;
}
function Oe(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function ke(e) {
	return !Oe(e, this.v);
}
function Ae(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function je() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Me(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function Ne(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Pe() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Fe(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Ie() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Le() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Re(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function ze() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Be() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ve() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function He() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var j = null;
function Ue(e) {
	j = e;
}
function We(t, n = !1, r) {
	j = {
		p: j,
		i: !1,
		c: null,
		e: null,
		s: t,
		x: null,
		r: G,
		l: e && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ge(e) {
	var t = j, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) mn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, j = t.p, Ke(e);
}
function Ke(e = {}) {
	return u(e, le, { value: !0 }), e;
}
function qe() {
	return !e || j !== null && j.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Je = [];
function Ye() {
	var e = Je;
	Je = [], y(e);
}
function Xe(e) {
	if (Je.length === 0 && !xt) {
		var t = Je;
		queueMicrotask(() => {
			t === Je && Ye();
		});
	}
	Je.push(e);
}
function Ze() {
	for (; Je.length > 0;) Ye();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var Qe = ~(S | C | x);
function M(e, t) {
	e.f = e.f & Qe | t;
}
function $e(e) {
	e.f & 512 || e.deps === null ? M(e, x) : M(e, C);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function et(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), M(e, x);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var tt = !1;
function nt() {
	tt || (tt = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ge]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function rt(e) {
	var t = U, n = G;
	W(null), Rn(null);
	try {
		return e();
	} finally {
		W(t), Rn(n);
	}
}
function it(e, t, n, r = n) {
	e.addEventListener(t, () => rt(n));
	let i = e[ge];
	e[ge] = i ? () => {
		i(), r(!0);
	} : () => r(!0), nt();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function at(e, t, n, r) {
	let i = qe() ? lt : ft;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = ot(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				cn(e, s);
			}
			st();
		}
	}
	var d = ct();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ dt(e))).then(u).catch((e) => cn(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), st();
	}) : f();
}
function ot() {
	var e = G, t = U, n = j, r = N;
	return function(i = !0) {
		Rn(e), W(t), Ue(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function st(e = !0) {
	Rn(null), W(null), Ue(null), e && N?.deactivate();
}
function ct() {
	var e = G, t = e.b, n = N, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function lt(e) {
	var t = 2 | S;
	return G !== null && (G.f |= E), {
		ctx: j,
		deps: null,
		effects: null,
		equals: De,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: r,
		wv: 0,
		parent: G,
		ac: null
	};
}
var ut = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function dt(e, t, n) {
	let i = G;
	i === null && je();
	var a = void 0, o = Rt(r), s = !U, c = /* @__PURE__ */ new Set();
	return yn(() => {
		var t = G, n = b();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== _e && n.reject(e);
			}).finally(st);
		} catch (e) {
			n.reject(e), st();
		}
		var r = N;
		if (s) {
			if (t.f & 32768) var l = ct();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(ut);
			else for (let e of c.values()) e.reject(ut);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== ut && (r.activate(), t ? (o.f |= se, Ht(o, t)) : (o.f & 8388608 && (o.f ^= se), Ht(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), fn(() => {
		for (let e of c) e.reject(ut);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/*#__NO_SIDE_EFFECTS__*/
function ft(e) {
	let t = /* @__PURE__ */ lt(e);
	return t.equals = ke, t;
}
function pt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) H(t[n]);
	}
}
function mt(e) {
	var t, n = G, i = e.parent;
	if (!Fn && i !== null && e.v !== r && i.f & 24576) return ye(), e.v;
	Rn(i);
	try {
		pt(e), t = Yn(e);
	} finally {
		Rn(n);
	}
	return t;
}
function ht(e) {
	var t = mt(e);
	if (!e.equals(t) && (e.wv = Kn(), (!N?.is_fork || e.deps === null) && (N === null ? e.v = t : (N.capture(e, t, !0), yt?.capture(e, t, !0)), e.deps === null))) {
		M(e, x);
		return;
	}
	Fn || (P === null ? $e(e) : (dn() || N?.is_fork) && P.set(e, t));
}
function gt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && rt(() => {
		t.ac.abort(_e), t.ac = null;
	}), t.fn !== null && (t.teardown = _), Qn(t, 0), wn(t));
}
function _t(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && $n(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var vt = null, N = null, yt = null, P = null, bt = null, xt = !1, St = !1, Ct = null, wt = null, Tt = 0, Et = 1, Dt = class e {
	id = Et++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = 0;
	#o = /* @__PURE__ */ new Map();
	#s = null;
	#c = [];
	#l = [];
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Map();
	#p = /* @__PURE__ */ new Set();
	is_fork = !1;
	#m = !1;
	constructor() {
		vt === null ? vt = this : (vt.#n = this, this.#t = vt), vt = this;
	}
	#h() {
		if (this.is_fork) return !0;
		for (let n of this.#o.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#f.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#f.has(e) || this.#f.set(e, {
			d: [],
			m: []
		}), this.#p.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#f.get(e);
		if (n) {
			this.#f.delete(e);
			for (var r of n.d) M(r, S), t(r);
			for (r of n.m) M(r, C), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		var e = [];
		for (let i of this.#c) if (!(i.f & 16384 || !(i.f & 6144))) {
			for (var t = i, n = !1; t.parent !== null;) {
				t = t.parent;
				var r = t.f;
				if (r & 96) {
					if (!(r & 1024)) {
						n = !0;
						break;
					}
					t.f ^= x;
				}
			}
			n || e.push(t);
		}
		return this.#c = [], e;
	}
	#_() {
		this.#e = !0;
		for (let e of this.#u) this.#d.delete(e), M(e, S), this.schedule(e);
		for (let e of this.#d) M(e, C), this.schedule(e);
		this.apply();
		for (var t = Ct = [], n = [], r = wt = []; this.#c.length > 0;) {
			Tt++ > 1e3 && (this.#S(), kt());
			for (let e of this.#g()) try {
				this.#v(e, t, n);
			} catch (t) {
				throw Pt(e), this.#h() || this.discard(), t;
			}
		}
		if (N = null, r.length > 0) {
			var i = e.ensure();
			for (let e of r) i.schedule(e);
		}
		if (Ct = null, wt = null, this.#h()) {
			this.#x(n), this.#x(t);
			for (let [e, t] of this.#f) Nt(e, t);
			r.length > 0 && N.#_();
			return;
		}
		let a = this.#y();
		if (a) {
			this.#x(n), this.#x(t), a.#b(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), yt = this, jt(n), jt(t), yt = null, this.#s?.resolve();
		var o = N;
		if (this.#a === 0 && (this.#c.length === 0 || o !== null) && this.#S(), this.#c.length > 0) {
			if (o !== null) {
				for (let e of this.#c) o.#c.push(e);
				this.#c = [];
			} else o = this;
		}
		o !== null && (It.clear(), o.#_());
	}
	#v(e, t, n) {
		e.f ^= x;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= x : i & 4 ? t.push(r) : qn(r) && (i & 16 && this.#d.add(r), $n(r));
				var o = r.first;
				if (o !== null) {
					r = o;
					continue;
				}
			}
			for (; r !== null;) {
				var s = r.next;
				if (s !== null) {
					r = s;
					break;
				}
				r = r.parent;
			}
		}
	}
	#y() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#b(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_effects(e.#u, e.#d);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null && !(e.f & 2 && !(e.f & 6144))) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), M(i, S), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#S(), N = this, this.#_();
	}
	#x(e) {
		for (var t = 0; t < e.length; t += 1) et(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== r && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), P?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		N = this;
	}
	deactivate() {
		N = null, P = null;
	}
	flush() {
		try {
			St = !0, N = this, this.#_();
		} finally {
			Tt = 0, bt = null, Ct = null, wt = null, St = !1, N = null, P = null, It.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(ut);
		this.#S(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
	}
	increment(e, t) {
		if (this.#a += 1, e) {
			let e = this.#o.get(t) ?? 0;
			this.#o.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#a, e) {
			let e = this.#o.get(t) ?? 0;
			e === 1 ? this.#o.delete(t) : this.#o.set(t, e - 1);
		}
		this.#m || (this.#m = !0, Xe(() => {
			this.#m = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#u.add(t);
		for (let e of t) this.#d.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	settled() {
		return (this.#s ??= b()).promise;
	}
	static ensure() {
		if (N === null) {
			let t = N = new e();
			!St && !xt && Xe(() => {
				t.#e || t.flush();
			});
		}
		return N;
	}
	apply() {
		P = null;
	}
	schedule(e) {
		if (bt = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768)) {
			e.b.defer_effect(e);
			return;
		}
		this.#c.push(e);
	}
	#S() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null || (e.#n = t), t === null ? vt = e : t.#t = e, this.linked = !1;
		}
	}
};
function Ot(e) {
	var t = xt;
	xt = !0;
	try {
		var n;
		for (e && (N !== null && !N.is_fork && N.flush(), n = e());;) {
			if (Ze(), N === null) return n;
			N.flush();
		}
	} finally {
		xt = t;
	}
}
function kt() {
	try {
		Ie();
	} catch (e) {
		cn(e, bt);
	}
}
var At = null;
function jt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && qn(r) && (At = /* @__PURE__ */ new Set(), $n(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Dn(r), At?.size > 0)) {
				It.clear();
				for (let e of At) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) At.has(n) && (At.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || $n(n);
					}
				}
				At.clear();
			}
		}
		At = null;
	}
}
function Mt(e) {
	N.schedule(e);
}
function Nt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), M(e, x);
		for (var n = e.first; n !== null;) Nt(n, t), n = n.next;
	}
}
function Pt(e) {
	M(e, x);
	for (var t = e.first; t !== null;) Pt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Ft = /* @__PURE__ */ new Set(), It = /* @__PURE__ */ new Map(), Lt = !1;
function Rt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: De,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function zt(e, t) {
	let n = Rt(e, t);
	return Bn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function F(t, n = !1, r = !0) {
	let i = Rt(t);
	return n || (i.equals = ke), e && r && j !== null && j.l !== null && (j.l.s ??= []).push(i), i;
}
function I(e, t, n = !1) {
	return U !== null && (!Ln || U.f & 131072) && qe() && U.f & 4325394 && (zn === null || !zn.has(e)) && Ve(), Ht(e, n ? Kt(t) : t, wt);
}
var Bt = null, Vt = 0;
function Ht(e, t, n = null) {
	if (!e.equals(t)) {
		Fn ? It.set(e, t) : It.has(e) || It.set(e, e.v);
		var r = Dt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && mt(t), P === null && $e(t);
		}
		e.wv = Kn(), Bt = null, Vt = 0, Gt(e, S, n), Bt = null, qe() && G !== null && G.f & 1024 && !(G.f & 96) && (J === null ? Vn([e]) : J.push(e)), !r.is_fork && Ft.size > 0 && !Lt && Ut();
	}
	return t;
}
function Ut() {
	Lt = !1;
	for (let e of Ft) {
		e.f & 1024 && M(e, C);
		let t;
		try {
			t = qn(e);
		} catch {
			t = !0;
		}
		t && $n(e);
	}
	Ft.clear();
}
function Wt(e) {
	I(e, e.v + 1);
}
function Gt(e, t, n) {
	var r = e.reactions;
	if (r !== null) {
		var i = qe(), a = r.length;
		if (Vt += a, Vt > 1e5 && Bt === null && (Bt = /* @__PURE__ */ new Set()), Bt !== null) {
			if (Bt.has(e)) return;
			Bt.add(e);
		}
		for (var o = 0; o < a; o++) {
			var s = r[o], c = s.f;
			if (i || s !== G) {
				var l = (c & S) === 0;
				if (l && M(s, t), c & 131072) Ft.add(s);
				else if (c & 2) {
					var u = s;
					P?.delete(u), Gt(u, C, n);
				} else if (l) {
					var d = s;
					c & 16 && At !== null && At.add(d), n === null ? Mt(d) : n.push(d);
				}
			}
		}
	}
}
function Kt(e) {
	if (typeof e != "object" || !e || ce in e || le in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ zt(0), s = null, c = Wn, l = (e) => {
		if (Wn === c) return e();
		var t = U, n = Wn;
		W(null), Gn(c);
		var r = e();
		return W(t), Gn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ zt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && ze();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ zt(r.value, s);
				return n.set(t, e), e;
			}) : I(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ zt(r, s));
					n.set(t, e), Wt(o);
				}
			} else I(i, r), Wt(o);
			return !0;
		},
		get(t, i, a) {
			if (i === ce) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ zt(Kt(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = Y(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var i = Reflect.getOwnPropertyDescriptor(e, t), a = n.get(t);
			if (a !== void 0) {
				var o = Y(a);
				if (o === r) return;
				if (i && "value" in i) i.value = o;
				else return {
					enumerable: !0,
					configurable: !0,
					value: o,
					writable: !0
				};
			}
			return i;
		},
		has(e, t) {
			if (t === ce) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || G !== null && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ zt(a ? Kt(e[t]) : r, s)), n.set(t, i)), Y(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ zt(r, s)), n.set(p + "", m)) : I(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ zt(void 0, s)), I(u, Kt(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => Kt(a));
				I(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && I(_, v + 1);
				}
				Wt(o);
			}
			return !0;
		},
		ownKeys(e) {
			Y(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== r;
			});
			for (var [i, a] of n) a.v !== r && !(i in e) && t.push(i);
			return t;
		},
		setPrototypeOf() {
			Be();
		}
	});
}
var qt, Jt, Yt, Xt;
function Zt() {
	if (qt === void 0) {
		qt = window, Jt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Yt = d(t, "firstChild").get, Xt = d(t, "nextSibling").get, g(e) && (e[pe] = void 0, e[fe] = null, e[me] = void 0, e.__e = void 0), g(n) && (n[he] = void 0);
	}
}
function L(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Qt(e) {
	return Yt.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function $t(e) {
	return Xt.call(e);
}
function R(e, t) {
	if (!D) return /* @__PURE__ */ Qt(e);
	var n = /* @__PURE__ */ Qt(O);
	if (n === null) n = O.appendChild(L());
	else if (t && n.nodeType !== 3) {
		var r = L();
		return n?.before(r), k(r), r;
	}
	return t && on(n), k(n), n;
}
function en(e, t = !1) {
	if (!D) {
		var n = /* @__PURE__ */ Qt(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ $t(n) : n;
	}
	if (t) {
		if (O?.nodeType !== 3) {
			var r = L();
			return O?.before(r), k(r), r;
		}
		on(O);
	}
	return O;
}
function tn(e, t = !1) {
	if (!D) return /* @__PURE__ */ Qt(e);
	var n = R(e, t);
	return A(e), n;
}
function z(e, t = 1, n = !1) {
	let r = D ? O : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ $t(r);
	if (!D) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = L();
			return r === null ? i?.after(a) : r.before(a), k(a), a;
		}
		on(r);
	}
	return k(r), r;
}
function nn(e) {
	e.textContent = "";
}
function rn() {
	return !1;
}
function an(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function on(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function sn(e) {
	var t = G;
	if (t === null) return U.f |= se, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	cn(e, t);
}
function cn(e, t) {
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128 && !(t.f & 33570816)) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function ln(e) {
	G === null && (U === null && Fe(e), Pe()), Fn && Ne(e);
}
function un(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function B(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= w);
	var r = {
		ctx: j,
		deps: null,
		nodes: null,
		f: e | S | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	N?.register_created_effect(r);
	var i = r;
	if (e & 4) Ct === null ? Dt.ensure().schedule(r) : Ct.push(r);
	else if (t !== null) {
		try {
			$n(r);
		} catch (e) {
			throw H(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= T));
	}
	if (i !== null && (i.parent = n, n !== null && un(i, n), U !== null && U.f & 2 && !(e & 64))) {
		var a = U;
		(a.effects ??= []).push(i);
	}
	return r;
}
function dn() {
	return U !== null && !Ln;
}
function fn(e) {
	let t = B(8, null);
	return M(t, x), t.teardown = e, t;
}
function pn(e) {
	ln("$effect");
	var t = G.f;
	if (!U && t & 32 && j !== null && !j.i) {
		var n = j;
		(n.e ??= []).push(e);
	} else return mn(e);
}
function mn(e) {
	return B(4 | re, e);
}
function hn(e) {
	return ln("$effect.pre"), B(8 | re, e);
}
function gn(e) {
	Dt.ensure();
	let t = B(64 | E, e);
	return () => {
		H(t);
	};
}
function _n(e) {
	Dt.ensure();
	let t = B(64 | E, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? On(t, () => {
			H(t), n(void 0);
		}) : (H(t), n(void 0));
	});
}
function vn(e) {
	return B(4, e);
}
function yn(e) {
	return B(oe | E, e);
}
function bn(e, t = 0) {
	return B(8 | t, e);
}
function xn(e, t = [], n = [], r = []) {
	at(r, t, n, (t) => {
		B(8, () => {
			e(...t.map(Y));
		});
	});
}
function Sn(e, t = 0) {
	return B(16 | t, e);
}
function V(e) {
	return B(32 | E, e);
}
function Cn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = Fn, r = U;
		In(!0), W(null);
		try {
			t.call(null);
		} catch (t) {
			cn(t, e.parent);
		} finally {
			In(n), W(r);
		}
	}
}
function wn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && rt(() => {
			e.abort(_e);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : H(n, t), n = r;
	}
}
function Tn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || H(t), t = n;
	}
}
function H(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (En(e.nodes.start, e.nodes.end), n = !0), e.f |= ne, wn(e, t && !n), Qn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Cn(e), e.f ^= ne, e.f |= ee;
	var i = e.parent;
	i !== null && i.first !== null && Dn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function En(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ $t(e);
		e.remove(), e = n;
	}
}
function Dn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function On(e, t, n = !0) {
	var r = [];
	e.f |= 256, kn(e, r, !0);
	var i = () => {
		n && H(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function kn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= w;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				kn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function An(e) {
	e.f &= -257, jn(e, !0);
}
function jn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= w, e.f & 1024 || (M(e, S), Dt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			jn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Mn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ $t(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Nn = null, Pn = !1, Fn = !1;
function In(e) {
	Fn = e;
}
var U = null, Ln = !1;
function W(e) {
	U = e;
}
var G = null;
function Rn(e) {
	G = e;
}
var zn = null;
function Bn(e) {
	U !== null && (U.f & 2097152 || U.f & 2) && (zn ??= /* @__PURE__ */ new Set()).add(e);
}
var K = null, q = 0, J = null;
function Vn(e) {
	J = e;
}
var Hn = 1, Un = 0, Wn = Un;
function Gn(e) {
	Wn = e;
}
function Kn() {
	return ++Hn;
}
function qn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (qn(a) && ht(a), a.wv > e.wv) return !0;
		}
		t & 512 && P === null && M(e, x);
	}
	return !1;
}
function Jn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(zn !== null && zn.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Jn(a, t, !1) : t === a && (n ? M(a, S) : a.f & 1024 && M(a, C), Mt(a));
	}
}
function Yn(e) {
	var t = K, n = q, r = J, i = U, a = zn, o = j, s = Ln, c = Wn, l = e.f;
	K = null, q = 0, J = null, U = l & 96 ? null : e, zn = null, Ue(e.ctx), Ln = !1, Wn = ++Un, e.ac !== null && (rt(() => {
		e.ac.abort(_e);
	}), e.ac = null);
	try {
		e.f |= ae;
		var u = e.fn, d = u();
		e.f |= te;
		var f = Xn(e);
		if (qe() && J !== null && !Ln && f !== null && !(e.f & 6146)) for (var p = 0; p < J.length; p++) Jn(J[p], e);
		if (i !== null && i !== e) {
			if (Un++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Un;
			if (t !== null) for (let e of t) e.rv = Un;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= se), d;
	} catch (t) {
		return Xn(e), sn(t);
	} finally {
		e.f ^= ae, K = t, q = n, J = r, U = i, zn = a, Ue(o), Ln = s, Wn = c;
	}
}
function Xn(e) {
	var t = e.deps, n = N?.is_fork;
	if (K !== null) {
		var r;
		if (n || Qn(e, q), t !== null && q > 0) for (t.length = q + K.length, r = 0; r < K.length; r++) t[q + r] = K[r];
		else e.deps = t = K;
		if (dn() && e.f & 512) for (r = q; r < t.length; r++) (t[r].reactions ??= []).push(e);
	} else !n && t !== null && q < t.length && (Qn(e, q), t.length = q);
	return t;
}
function Zn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (K === null || !s.call(K, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512), c.v !== r && $e(c), c.ac !== null && rt(() => {
			c.ac.abort(_e), c.ac = null, M(c, S);
		}), gt(c), Qn(c, 0);
	}
}
function Qn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Zn(e, n[r]);
}
function $n(e) {
	var t = e.f;
	if (!(t & 16384)) {
		M(e, x);
		var n = G, r = Pn;
		G = e, Pn = !(t & 96);
		try {
			t & 16777232 ? Tn(e) : wn(e), Cn(e);
			var i = Yn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Hn;
		} finally {
			Pn = r, G = n;
		}
	}
}
async function er() {
	await Promise.resolve(), Ot();
}
function Y(e) {
	var t = !!(e.f & 2);
	if (Nn?.add(e), U !== null && !Ln && !(G !== null && G.f & 16384) && (zn === null || !zn.has(e))) {
		var n = U.deps;
		if (U.f & 2097152) e.rv < Un && (e.rv = Un, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			U.deps ??= [], s.call(U.deps, e) || U.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [U] : s.call(r, U) || r.push(U);
		}
	}
	if (Fn && It.has(e)) return It.get(e);
	if (t) {
		var i = e;
		if (Fn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || nr(i)) && (a = mt(i)), It.set(i, a), a;
		}
		var o = !(i.f & 512) && !Ln && U !== null && (Pn || !!(U.f & 512)), c = (i.f & te) === 0;
		qn(i) && (o && (i.f |= 512), ht(i)), o && !c && (_t(i), tr(i));
	}
	if (P?.has(e)) return P.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function tr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (_t(t), tr(t));
}
function nr(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (It.has(t) || t.f & 2 && nr(t)) return !0;
	return !1;
}
function X(e) {
	var t = Ln;
	try {
		return Ln = !0, e();
	} finally {
		Ln = t;
	}
}
function rr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (ce in e) ir(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && ce in n && ir(n);
		}
	}
}
function ir(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			ir(e[n], t);
		} catch {}
		let n = h(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = f(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var ar = Symbol("events"), or = /* @__PURE__ */ new Set(), sr = /* @__PURE__ */ new Set();
function cr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || dr.call(t, e), !e.cancelBubble) return rt(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? (i.__removed = !1, Xe(() => {
		i.__removed || t.addEventListener(e, i, r);
	})) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = cr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && fn(() => {
		o.__removed = !0, t.removeEventListener(e, o, a);
	});
}
var lr = null, ur = !1;
function dr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	lr = e, ur || (ur = !0, setTimeout(() => {
		ur = !1, lr = null;
	}));
	var o = 0, s = lr === e && e[ar];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[ar] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		u(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var d = U, f = G;
		W(null), Rn(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[ar]?.[r];
					h != null && (!a.disabled || e.target === a) && h.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				o++, a = o < i.length ? i[o] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[ar] = t, delete e.currentTarget, W(d), Rn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var fr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function pr(e) {
	return fr?.createHTML(e) ?? e;
}
function mr(e) {
	var t = an("template");
	return t.innerHTML = pr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function hr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (D) return hr(O, null), O;
		i === void 0 && (i = mr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Qt(i)));
		var t = r || Jt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ Qt(t), s = t.lastChild;
			hr(o, s);
		} else hr(t, t);
		return t;
	};
}
function $(e, t) {
	if (D) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = O), Ce();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var gr = ["touchstart", "touchmove"];
function _r(e) {
	return gr.includes(e);
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function vr(e) {
	let t = 0, n = Rt(0), r;
	return () => {
		dn() && (Y(n), bn(() => (t === 0 && (r = X(() => e(() => Wt(n)))), t += 1, () => {
			Xe(() => {
				--t, t === 0 && (r?.(), r = void 0, Wt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var yr = T | E;
function br(e, t, n, r) {
	new xr(e, t, n, r);
}
var xr = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = D ? O : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = vr(() => (this.#m = Rt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Sn(() => {
			if (D) {
				let e = this.#t;
				Ce();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#y() : this.#g();
			} else this.#b();
		}, yr), D && (this.#e = O);
	}
	#g() {
		try {
			this.#a = V(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#v(e);
		Xe(r), t && (this.#s = V(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#v(e) {
		var t = !1, n = !1;
		let r = () => {
			if (t) {
				xe();
				return;
			}
			t = !0, n && He(), this.#s !== null && On(this.#s, () => {
				this.#s = null;
			}), this.#S(() => {
				this.#b();
			});
		};
		return {
			reset: r,
			invoke_onerror: () => {
				try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					cn(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = V(() => e(this.#e)), Xe(() => {
			var e = this.#c = document.createDocumentFragment(), t = L(), n = !1;
			if (e.append(t), this.#a = this.#S(() => {
				try {
					return V(() => this.#r(t));
				} catch (e) {
					try {
						this.error(e), n = !0;
					} catch (e) {
						cn(e, this.#i.parent);
					}
					return null;
				}
			}), this.#a === null) {
				this.#c = null, n && this.#x(N);
				return;
			}
			this.#u === 0 && (this.#e.before(e), this.#c = null, On(this.#o, () => {
				this.#o = null;
			}), this.#x(N));
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = V(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Mn(this.#a, e);
				let t = this.#n.pending;
				this.#o = V(() => t(this.#e));
			} else this.#x(N);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		et(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = G, n = U, r = j;
		Rn(this.#i), W(this.#i), Ue(this.#i.ctx);
		try {
			return Dt.ensure(), e();
		} finally {
			Rn(t), W(n), Ue(r);
		}
	}
	#C(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#C(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#x(t), this.#o && On(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Xe(() => {
			this.#d = !1, this.#m && Ht(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Y(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		N?.is_fork ? (this.#a && N.skip_effect(this.#a), this.#o && N.skip_effect(this.#o), this.#s && N.skip_effect(this.#s), N.oncommit(() => {
			this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (H(this.#a), null), this.#o &&= (H(this.#o), null), this.#s &&= (H(this.#s), null), D && (k(this.#t), we(), k(Te()));
		let t = this.#n.failed, n = (e) => {
			let { reset: n, invoke_onerror: r } = this.#v(e);
			r(), t && (this.#s = this.#S(() => {
				try {
					return V(() => {
						var r = G;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return cn(e, this.#i.parent), null;
				}
			}));
		};
		Xe(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				cn(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => cn(e, this.#i && this.#i.parent)) : n(t);
		});
	}
};
function Sr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[he] ??= e.nodeValue) && (e[he] = n, e.nodeValue = `${n}`);
}
function Cr(e, t) {
	return Er(e, t);
}
function wr(e, t) {
	Zt(), t.intro = t.intro ?? !1;
	let r = t.target, i = D, a = O;
	try {
		for (var o = /* @__PURE__ */ Qt(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ $t(o);
		if (!o) throw n;
		Se(!0), k(o);
		let i = Er(e, {
			...t,
			anchor: o
		});
		return Se(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && Le(), Zt(), nn(r), Se(!1), Cr(e, t);
	} finally {
		Se(i), k(a);
	}
}
var Tr = /* @__PURE__ */ new Map();
function Er(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	Zt();
	var u = void 0, d = _n(() => {
		var s = r ?? t.appendChild(L());
		br(s, { pending: () => {} }, (t) => {
			We({});
			var r = j;
			if (o && (r.c = o), a && (i.$$events = a), D && hr(t, null), u = e(t, i) || Ke(), D && (G.nodes.end = O, O === null || O.nodeType !== 8 || O.data !== "]")) throw be(), n;
			Ge();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = _r(r);
					for (let e of [t, document]) {
						var a = Tr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Tr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, dr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(or)), sr.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = Tr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, dr), n.delete(e), n.size === 0 && Tr.delete(r)) : n.set(e, i);
			}
			sr.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return Dr.set(u, d), u;
}
var Dr = /* @__PURE__ */ new WeakMap();
function Or(e, t) {
	let n = Dr.get(e);
	return n ? (Dr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var kr = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) An(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (An(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (H(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Mn(r, t), t.append(L()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else H(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), On(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (H(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = N, r = rn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = L();
				i.append(a), this.#n.set(e, {
					effect: V(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, V(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else D && (this.anchor = O), this.#a(n);
	}
};
function Ar(t) {
	j === null && Ae("onMount"), e && j.l !== null ? jr(j).m.push(t) : pn(() => {
		let e = X(t);
		if (typeof e == "function") return e;
	});
}
function jr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Mr(e, t, n = !1) {
	var r;
	D && (r = O, Ce());
	var i = new kr(e), a = n ? T : 0;
	function o(e, t) {
		if (D) {
			var n = Ee(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Te();
				k(a), i.anchor = a, Se(!1), i.ensure(e, t), Se(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Sn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Nr(e, t) {
	return t;
}
function Pr(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		On(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Fr(e, c(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var l = r.length === 0 && n !== null && e.pending.size === 0;
		if (l) {
			var u = n, d = u.parentNode;
			nn(d), d.append(u), e.items.clear();
		}
		Fr(e, t, !l);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Fr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= ie, Mn(a, document.createDocumentFragment())) : H(t[i], n);
	}
}
var Ir;
function Lr(e, t, n, r, i, o = null) {
	var s = e, l = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = D ? k(/* @__PURE__ */ Qt(u)) : u.appendChild(L());
	}
	D && Ce();
	var d = null, f = /* @__PURE__ */ ft(() => {
		var e = n();
		return a(e) ? e : e == null ? [] : c(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, zr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= ie, Vr(d, null, s)) : An(d) : On(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: Sn(() => {
			p = Y(f);
			var e = p.length;
			let a = !1;
			D && Ee(s) === "[!" != (e === 0) && (s = Te(), k(s), Se(!1), a = !0);
			for (var c = /* @__PURE__ */ new Set(), u = N, v = rn(), y = 0; y < e; y += 1) {
				D && O.nodeType === 8 && O.data === "]" && (s = O, a = !0, Se(!1));
				var b = p[y], x = r(b, y), S = h ? null : l.get(x);
				S ? (S.v && Ht(S.v, b), S.i && Ht(S.i, y), v && u.unskip_effect(S.e)) : (S = Br(l, h ? s : Ir ??= L(), b, x, y, i, t, n), h || (S.e.f |= ie), l.set(x, S)), c.add(x);
			}
			if (e === 0 && o && !d && (h ? d = V(() => o(s)) : (d = V(() => o(Ir ??= L())), d.f |= ie)), e > c.size && Me("", "", ""), D && e > 0 && k(Te()), !h) {
				if (m.set(u, c), v) {
					for (let [e, t] of l) c.has(e) || u.skip_effect(t.e);
					u.oncommit(g), u.ondiscard(_);
				} else g(u);
			}
			a && Se(!0), Y(f);
		}),
		flags: t,
		items: l,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, D && (s = O);
}
function Rr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function zr(e, t, n, r, i) {
	var a = !!(r & 8), o = t.length, s = e.items, l = Rr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (An(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) {
			if (_.f ^= ie, _ === l) Vr(_, null, n);
			else {
				var y = d ? d.next : l;
				_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Hr(e, d, _), Hr(e, _, y), Vr(_, y, n), d = _, p = [], m = [], l = Rr(d.next);
				continue;
			}
		}
		if (_ !== l) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Vr(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Hr(e, S.prev, C.next), Hr(e, d, S), Hr(e, C, b), l = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Vr(_, l, n), Hr(e, _.prev, _.next), Hr(e, _, d === null ? e.effect.first : d.next), Hr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; l !== null && l !== _;) (u ??= /* @__PURE__ */ new Set()).add(l), m.push(l), l = Rr(l.next);
			if (l === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, l = Rr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Fr(e, c(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (l !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; l !== null;) !(l.f & 8192) && l !== e.fallback && w.push(l), l = Rr(l.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			Pr(e, w, te);
		}
	}
	a && Xe(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Br(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Rt(n) : /* @__PURE__ */ F(n, !1, !1) : null, l = o & 2 ? Rt(i) : null;
	return {
		v: c,
		i: l,
		e: V(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Vr(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ $t(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Hr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Ur(e, t) {
	vn(() => {
		e = G?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = an("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var Wr = [..." 	\n\r\f\xA0\v﻿"];
function Gr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Wr.includes(r[o - 1])) && (s === r.length || Wr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Kr(e, t, n, r, i, a) {
	var o = e[pe];
	if (D || o !== n || o === void 0) {
		var s = Gr(n, r, a);
		(!D || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[pe] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var qr = Symbol("is custom element"), Jr = Symbol("is html"), Yr = ve ? "link" : "LINK", Xr = ve ? "progress" : "PROGRESS";
function Zr(e) {
	if (D) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					$r(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					$r(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ge] = n, Xe(n), nt();
	}
}
function Qr(e, t) {
	var n = ei(e);
	n.value !== (n.value = t ?? void 0) && (e.value !== t || t === 0 && e.nodeName === Xr) && (e.value = t ?? "");
}
function $r(e, t, n, r) {
	var i = ei(e);
	D && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Yr) || i[t] !== (i[t] = n) && (t === "loading" && (e[de] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && ni(e).has(t) ? e[t] = n : e.setAttribute(t, n));
}
function ei(e) {
	return e[fe] ??= {
		[qr]: e.nodeName.includes("-"),
		[Jr]: e.namespaceURI === i
	};
}
var ti = /* @__PURE__ */ new Map();
function ni(e) {
	var t = e.getAttribute("is") || e.nodeName, n = ti.get(t);
	if (n) return n;
	ti.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = h(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function ri(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	it(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = ii(e) ? ai(a) : a, n(a), N !== null && r.add(N), await er(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (D && e.defaultValue !== e.value || X(t) == null && e.value) && (n(ii(e) ? ai(e.value) : e.value), N !== null && r.add(N)), bn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = N;
			if (r.has(i)) return;
		}
		ii(e) && n === ai(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function ii(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function ai(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function oi(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function si(e = !1) {
	let t = j, n = t.l.u;
	if (!n) return;
	let r = () => rr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ lt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && hn(() => {
		ci(t, r), y(n.b);
	}), pn(() => {
		let e = X(() => n.m.map(v));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && pn(() => {
		ci(t, r), y(n.a);
	});
}
function ci(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function li(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of a(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var ui = !1;
function di(e) {
	var t = ui;
	try {
		return ui = !1, [e(), ui];
	} finally {
		ui = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function fi(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ lt(i), Y(u)) : (l && (l = !1, c = s ? X(i) : i), c);
	let p;
	if (o) {
		var m = ce in t || ue in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, g = !1;
	o ? [h, g] = di(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && Re(n), p(h)));
	var _ = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var v = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || v || g) && p(t ? _() : e), e) : _();
		});
	}
	var y = !1, b = (r & 1 ? lt : ft)(() => (y = !1, _()));
	o && Y(b);
	var x = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(b) : a && o ? Kt(e) : e;
			return I(b, n), y = !0, c !== void 0 && (c = n), e;
		}
		return Fn && y || x.f & 16384 ? b.v : Y(b);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function pi(e) {
	return new mi(e);
}
var mi = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ F(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Y(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === ue || (Y(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return I(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? wr : Cr)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), (!e?.props?.$$host || e.sync === !1) && Ot(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && u(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Or(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, hi;
typeof HTMLElement == "function" && (hi = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = an("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = _i(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = gi(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = pi({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = gn(() => {
				bn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = gi(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = gi(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return l(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function gi(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function _i(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function vi(e, t, n, r, i, a) {
	let o = class extends hi {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return l(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return l(t).forEach((e) => {
		u(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = gi(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (d(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		u(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region MusicBrainzCard.svelte
var yi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-1ghyjz5\">Loading...</div>"), bi = /* @__PURE__ */ Q("<div class=\"redirect-copy-group svelte-1ghyjz5\"><input type=\"text\" class=\"input-field readonly svelte-1ghyjz5\" readonly=\"\"/> <button class=\"btn-primary svelte-1ghyjz5\">Copy</button></div>"), xi = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-1ghyjz5\">+ Add Account</button>"), Si = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-1ghyjz5\">✓ Authenticated</span>"), Ci = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-1ghyjz5\">⚠ Not Authenticated</span>"), wi = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-1ghyjz5\">● Active</span>"), Ti = /* @__PURE__ */ Q("<div class=\"account-item svelte-1ghyjz5\"><div class=\"account-info svelte-1ghyjz5\"><div class=\"account-name svelte-1ghyjz5\"> </div> <div class=\"account-badges svelte-1ghyjz5\"><!> <!></div></div> <div class=\"account-actions svelte-1ghyjz5\"><button class=\"link-btn svelte-1ghyjz5\"> </button> <button> </button> <button class=\"btn-danger svelte-1ghyjz5\">✕</button></div></div>"), Ei = /* @__PURE__ */ Q("<div class=\"empty-accounts svelte-1ghyjz5\">No accounts linked.</div>"), Di = /* @__PURE__ */ Q("<div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Server Configuration</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">API Base URL</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"https://musicbrainz.org/ws/2\"/> <p class=\"helper-text svelte-1ghyjz5\">Point this to a local MusicBrainz container for offline use.</p></label> <button class=\"btn-primary svelte-1ghyjz5\">Save Settings</button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">OAuth Credentials</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client ID</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"Enter Client ID\"/></label> <label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client Secret</span> <div class=\"password-wrapper svelte-1ghyjz5\"><input class=\"input-field svelte-1ghyjz5\"/> <button class=\"toggle-visibility svelte-1ghyjz5\"> </button></div></label> <button class=\"btn-primary svelte-1ghyjz5\"> </button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Redirect URI</h3> <button class=\"btn-ghost svelte-1ghyjz5\"> </button></div> <!></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\"> </h3> <!></div> <div class=\"accounts-list svelte-1ghyjz5\"></div></div>", 1), Oi = /* @__PURE__ */ Q("<div class=\"modal-overlay svelte-1ghyjz5\"><div class=\"modal-content svelte-1ghyjz5\"><div class=\"modal-header svelte-1ghyjz5\"><h3 class=\"modal-title svelte-1ghyjz5\">Add MusicBrainz Account</h3> <button class=\"close-btn svelte-1ghyjz5\">✕</button></div> <div class=\"modal-body svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Display Name</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"My Account\"/></label></div> <div class=\"modal-footer svelte-1ghyjz5\"><button class=\"btn-ghost svelte-1ghyjz5\">Cancel</button> <button class=\"btn-primary svelte-1ghyjz5\">Add</button></div></div></div>"), ki = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-1ghyjz5\"><div class=\"card-header svelte-1ghyjz5\"><div class=\"header-left svelte-1ghyjz5\"><h2 class=\"card-title svelte-1ghyjz5\">MusicBrainz</h2> <span class=\"type-badge svelte-1ghyjz5\">Metadata Provider</span></div></div> <!></section> <!>", 1), Ai = {
	hash: "svelte-1ghyjz5",
	code: ".plugin-card.svelte-1ghyjz5 {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-1ghyjz5 {display:flex;align-items:center;gap:12px;}.card-title.svelte-1ghyjz5 {margin:0;font-size:20px;font-weight:700;}.type-badge.svelte-1ghyjz5 {font-size:11px;padding:4px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-1ghyjz5 {padding:24px;text-align:center;color:var(--text-secondary, #cbd5e1);}.settings-section.svelte-1ghyjz5 {margin-bottom:24px;}.section-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}.section-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:600;}.form-grid.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-1ghyjz5 {font-size:13px;font-weight:500;color:var(--text-secondary, #cbd5e1);}.input-field.svelte-1ghyjz5 {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-1ghyjz5:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.input-field.readonly.svelte-1ghyjz5 {opacity:0.6;cursor:not-allowed;}.btn-primary.svelte-1ghyjz5 {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-1ghyjz5:hover:not(:disabled) {opacity:0.9;}.btn-primary.svelte-1ghyjz5:disabled {opacity:0.5;cursor:not-allowed;}.btn-ghost.svelte-1ghyjz5 {padding:8px 16px;background:rgba(255, 255, 255, 0.05);border:1px solid rgba(255, 255, 255, 0.1);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-1ghyjz5:hover {background:rgba(255, 255, 255, 0.1);}.btn-ghost.active.svelte-1ghyjz5 {border-color:var(--color-primary, #14b8a6);color:var(--color-primary, #14b8a6);}.btn-danger.svelte-1ghyjz5 {background:rgba(239, 68, 68, 0.15);color:#ef4444;border:none;padding:8px 12px;border-radius:6px;cursor:pointer;}.helper-text.svelte-1ghyjz5 {font-size:11px;color:var(--text-secondary, #cbd5e1);margin-top:4px;}.redirect-copy-group.svelte-1ghyjz5 {display:flex;gap:8px;align-items:stretch;}.redirect-copy-group.svelte-1ghyjz5 .input-field:where(.svelte-1ghyjz5) {flex:1;font-family:monospace;}.accounts-list.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.account-item.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid rgba(255, 255, 255, 0.05);border-radius:8px;}.account-info.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-1ghyjz5 {font-weight:600;font-size:14px;}.account-badges.svelte-1ghyjz5 {display:flex;gap:8px;}.status-badge.svelte-1ghyjz5 {font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-1ghyjz5 {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-1ghyjz5 {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-1ghyjz5 {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.account-actions.svelte-1ghyjz5 {display:flex;gap:12px;align-items:center;}.link-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:600;cursor:pointer;}.link-btn.svelte-1ghyjz5:hover {text-decoration:underline;}.password-wrapper.svelte-1ghyjz5 {position:relative;display:flex;align-items:center;width:100%;}.toggle-visibility.svelte-1ghyjz5 {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.modal-overlay.svelte-1ghyjz5 {position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px);}.modal-content.svelte-1ghyjz5 {background:#0f1216;border:1px solid var(--border-subtle, #1e293b);border-radius:12px;width:100%;max-width:440px;box-shadow:0 24px 48px rgba(0,0,0,0.5);}.modal-header.svelte-1ghyjz5 {padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;}.modal-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:700;}.close-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--text-secondary, #cbd5e1);font-size:20px;cursor:pointer;}.modal-body.svelte-1ghyjz5 {padding:20px;display:flex;flex-direction:column;gap:16px;}.modal-footer.svelte-1ghyjz5 {padding:16px 20px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;gap:12px;}.empty-accounts.svelte-1ghyjz5 {text-align:center;padding:16px;color:var(--text-secondary, #cbd5e1);font-size:13px;background:rgba(255, 255, 255, 0.02);border-radius:8px;border:1px dashed rgba(255, 255, 255, 0.1);}"
};
function ji(e, t) {
	We(t, !1), Ur(e, Ai);
	let n = fi(t, "apiBase", 12, ""), r = /* @__PURE__ */ F(!0), i = /* @__PURE__ */ F([]), a = /* @__PURE__ */ F(""), o = /* @__PURE__ */ F(""), s = /* @__PURE__ */ F(""), c = /* @__PURE__ */ F(""), l = !1, u = !1, d = /* @__PURE__ */ F(!1), f = /* @__PURE__ */ F(!1), p = /* @__PURE__ */ F(!1), m = /* @__PURE__ */ F("https://musicbrainz.org/ws/2"), h = /* @__PURE__ */ F(!1), g = /* @__PURE__ */ F(""), _ = /* @__PURE__ */ F(!1);
	Ar(async () => {
		await v(), I(r, !1);
	});
	async function v() {
		try {
			let e = await (await fetch(`${n()}/accounts`)).json();
			e && (I(i, e.accounts || []), I(a, e.redirect_uri || ""), l = e.client_id_configured || !1, u = e.client_secret_configured || !1, I(p, !!Y(a)));
			let t = await (await fetch(`${n()}/settings`)).json();
			t?.settings && I(m, t.settings.api_base_url || "https://musicbrainz.org/ws/2");
			let r = await (await fetch(`${n()}/credentials`)).json();
			r?.credentials && (I(o, r.credentials.client_id || ""), I(c, u ? "••••••••" : ""));
		} catch (e) {
			console.error("Failed to load MusicBrainz data:", e);
		}
	}
	async function y() {
		if (!Y(o).trim()) {
			console.error("Client ID is required");
			return;
		}
		let e = { client_id: Y(o) };
		if (Y(s).trim()) e.client_secret = Y(s);
		else if (!u) {
			console.error("Client Secret is required");
			return;
		}
		try {
			I(f, !0), await fetch(`${n()}/credentials`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ credentials: e })
			}), I(s, ""), await v();
		} catch (e) {
			console.error("Failed to save credentials:", e);
		} finally {
			I(f, !1);
		}
	}
	async function b() {
		try {
			await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ settings: { api_base_url: Y(m) } })
			}), console.log("MusicBrainz settings saved");
		} catch (e) {
			console.error("Failed to save settings:", e);
		}
	}
	function x() {
		I(g, ""), I(h, !0);
	}
	function S() {
		I(h, !1), I(g, "");
	}
	async function C() {
		let e = Y(g).trim();
		if (e) try {
			I(_, !0), await fetch(`${n()}/accounts`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ account_name: e })
			}), S(), await v();
		} catch (e) {
			console.error("Failed to add account:", e);
		} finally {
			I(_, !1);
		}
	}
	async function w(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/accounts/${e}`, { method: "DELETE" }), await v();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function ee(e, t) {
		try {
			await fetch(`${n()}/accounts/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), await v();
		} catch (e) {
			console.error("Failed to update account status:", e);
		}
	}
	async function te(e) {
		if (!l || !u) {
			alert("Save your Client ID and Secret first.");
			return;
		}
		try {
			let t = (await (await fetch(`${n()}/auth?account_id=${e}`)).json())?.auth_url;
			t && (window.open(t, "_blank", "noopener,noreferrer"), setTimeout(() => v(), 5e3));
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var ne = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Ot();
		}
	};
	si();
	var T = ki(), E = en(T), re = z(R(E), 2), ie = (e) => {
		$(e, yi());
	}, ae = (e) => {
		var t = Di(), n = en(t), r = z(R(n), 2), l = R(r), u = z(R(l), 2);
		Zr(u), we(2), A(l);
		var h = z(l, 2);
		A(r), A(n);
		var g = z(n, 2), _ = z(R(g), 2), v = R(_), S = z(R(v), 2);
		Zr(S), A(v);
		var C = z(v, 2), ne = z(R(C), 2), T = R(ne);
		Zr(T);
		var E = z(T, 2), re = tn(E, !0);
		A(ne), A(C);
		var ie = z(C, 2), ae = tn(ie, !0);
		A(_), A(g);
		var oe = z(g, 2), se = R(oe), ce = z(R(se), 2), le = tn(ce, !0);
		A(se);
		var ue = z(se, 2), de = (e) => {
			var t = bi(), n = R(t);
			Zr(n);
			var r = z(n, 2);
			A(t), xn(() => Qr(n, Y(a))), Z("click", r, () => {
				navigator.clipboard.writeText(Y(a)), alert("Copied!");
			}), $(e, t);
		};
		Mr(ue, (e) => {
			Y(p) || e(de);
		}), A(oe);
		var fe = z(oe, 2), pe = R(fe), me = R(pe), he = tn(me), ge = z(me, 2), _e = (e) => {
			var t = xi();
			Z("click", t, x), $(e, t);
		};
		Mr(ge, (e) => {
			Y(i), X(() => Y(i).length < 10) && e(_e);
		}), A(pe);
		var ve = z(pe, 2);
		Lr(ve, 5, () => Y(i), Nr, (e, t) => {
			var n = Ti(), r = R(n), i = R(r), a = tn(i, !0), o = z(i, 2), s = R(o), c = (e) => {
				$(e, Si());
			}, l = (e) => {
				$(e, Ci());
			};
			Mr(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = z(s, 2), d = (e) => {
				$(e, wi());
			};
			Mr(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			}), A(o), A(r);
			var f = z(r, 2), p = R(f), m = tn(p, !0), h = z(p, 2);
			let g;
			var _ = tn(h, !0), v = z(h, 2);
			A(f), A(n), xn(() => {
				Sr(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), Sr(m, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), g = Kr(h, 1, "btn-ghost svelte-1ghyjz5", null, g, { active: Y(t).is_active }), Sr(_, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", p, () => te(Y(t).id)), Z("click", h, () => ee(Y(t).id, Y(t).is_active)), Z("click", v, () => w(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, Ei());
		}), A(ve), A(fe), xn(() => {
			$r(T, "type", Y(d) ? "text" : "password"), $r(T, "placeholder", Y(c) || "Enter Client Secret"), Sr(re, Y(d) ? "🙈" : "👁️"), ie.disabled = Y(f), Sr(ae, Y(f) ? "Saving..." : "Save Credentials"), Sr(le, Y(p) ? "Expand" : "Collapse"), Sr(he, `Accounts (${Y(i), X(() => Y(i).length) ?? ""}/10)`);
		}), ri(u, () => Y(m), (e) => I(m, e)), Z("click", h, b), ri(S, () => Y(o), (e) => I(o, e)), ri(T, () => Y(s), (e) => I(s, e)), Z("click", E, () => I(d, !Y(d))), Z("click", ie, y), Z("click", ce, () => I(p, !Y(p))), $(e, t);
	};
	Mr(re, (e) => {
		Y(r) ? e(ie) : e(ae, -1);
	}), A(E);
	var oe = z(E, 2), se = (e) => {
		var n = Oi(), r = R(n), i = R(r), a = z(R(i), 2);
		A(i);
		var o = z(i, 2), s = R(o), c = z(R(s), 2);
		Zr(c), A(s), A(o);
		var l = z(o, 2), u = R(l), d = z(u, 2);
		A(l), A(r), A(n), xn(() => d.disabled = Y(_)), Z("click", a, S), ri(c, () => Y(g), (e) => I(g, e)), Z("click", u, S), Z("click", d, C), Z("click", r, oi(function(e) {
			li.call(this, t, e);
		})), Z("click", n, S), $(e, n);
	};
	return Mr(oe, (e) => {
		Y(h) && e(se);
	}), $(e, T), Ge(ne);
}
customElements.define("musicbrainz-dashboard-card", vi(ji, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
//#region MusicBrainzSettingsCard.svelte
var Mi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-18cwlk6\">Loading configuration…</div>"), Ni = /* @__PURE__ */ Q("<span class=\"status-tag success svelte-18cwlk6\">● Configured</span>"), Pi = /* @__PURE__ */ Q("<div class=\"warning-box svelte-18cwlk6\">⚠ A User Token is required to enable contributions. Please enter your token above.</div>"), Fi = /* @__PURE__ */ Q("<div class=\"feedback error svelte-18cwlk6\"> </div>"), Ii = /* @__PURE__ */ Q("<div class=\"feedback success svelte-18cwlk6\">✓ Configuration saved successfully.</div>"), Li = /* @__PURE__ */ Q("<div class=\"info-banner svelte-18cwlk6\"><p>MusicBrainz works out-of-the-box for metadata retrieval. An account is only needed for contributing data back to the community.</p></div> <div class=\"form-section svelte-18cwlk6\"><label class=\"field-label svelte-18cwlk6\" for=\"mb-user-token\">User Token / API Key <!></label> <p class=\"helper-text svelte-18cwlk6\">Obtain your personal access token from <a href=\"https://musicbrainz.org/account/applications\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"link svelte-18cwlk6\">musicbrainz.org/account/applications</a>.\n        Required for submitting ISRC codes and metadata corrections.</p> <div class=\"input-wrapper svelte-18cwlk6\"><input id=\"mb-user-token\" class=\"input-field svelte-18cwlk6\"/> <button type=\"button\" class=\"toggle-btn svelte-18cwlk6\"> </button></div></div> <div class=\"toggle-card svelte-18cwlk6\"><div class=\"toggle-header svelte-18cwlk6\"><p class=\"toggle-label svelte-18cwlk6\">Auto-Contribute Missing Data</p> <button type=\"button\" role=\"switch\" aria-label=\"Toggle auto-contribute\"><span class=\"switch-thumb svelte-18cwlk6\"></span></button></div> <p class=\"helper-text mt-2 svelte-18cwlk6\">When enabled, EchoSync will automatically submit missing acoustic fingerprints (AcoustID) and \n        ISRC data back to MusicBrainz during imports.</p> <!></div> <!> <!> <div class=\"actions svelte-18cwlk6\"><button class=\"btn-primary svelte-18cwlk6\"> </button></div>", 1), Ri = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-18cwlk6\"><div class=\"card-header svelte-18cwlk6\"><svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"accent-icon svelte-18cwlk6\"><circle cx=\"12\" cy=\"12\" r=\"10\"></circle><path d=\"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3\"></path><line x1=\"12\" y1=\"17\" x2=\"12.01\" y2=\"17\"></line></svg> <div><h2 class=\"card-title svelte-18cwlk6\">MusicBrainz Configuration</h2> <p class=\"card-subtitle svelte-18cwlk6\">Global music encyclopedia & metadata source</p></div> <span class=\"type-badge svelte-18cwlk6\">Metadata</span></div> <!></section>"), zi = {
	hash: "svelte-18cwlk6",
	code: ".plugin-card.svelte-18cwlk6 {background:var(--bg-surface);backdrop-filter:blur(12px);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;margin-bottom:16px;color:var(--text-primary);}.card-header.svelte-18cwlk6 {display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle);}.accent-icon.svelte-18cwlk6 {color:var(--color-primary);}.card-title.svelte-18cwlk6 {margin:0;font-size:1.25rem;font-weight:600;line-height:1.2;}.card-subtitle.svelte-18cwlk6 {margin:4px 0 0;font-size:0.75rem;color:var(--text-muted);}.type-badge.svelte-18cwlk6 {margin-left:auto;font-size:11px;padding:4px 8px;background:rgba(16, 185, 129, 0.1);color:#10b981;border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-18cwlk6 {padding:20px;text-align:center;color:var(--text-muted);}.info-banner.svelte-18cwlk6 {margin-bottom:24px;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:8px;font-size:0.8125rem;color:var(--text-muted);line-height:1.4;}.form-section.svelte-18cwlk6 {margin-bottom:24px;}.field-label.svelte-18cwlk6 {display:block;font-size:0.875rem;font-weight:500;margin-bottom:4px;}.status-tag.success.svelte-18cwlk6 {margin-left:8px;font-size:11px;padding:2px 6px;background:rgba(16, 185, 129, 0.15);color:#10b981;border-radius:4px;}.helper-text.svelte-18cwlk6 {font-size:0.75rem;color:var(--text-muted);margin-bottom:8px;line-height:1.5;}.link.svelte-18cwlk6 {color:var(--color-primary);text-decoration:none;}.link.svelte-18cwlk6:hover {text-decoration:underline;}.input-wrapper.svelte-18cwlk6 {position:relative;display:flex;align-items:center;}.input-field.svelte-18cwlk6 {width:100%;padding:10px 14px;padding-right:40px;background:rgba(0, 0, 0, 0.2);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);color:var(--text-primary);font-size:0.875rem;transition:border-color 0.2s;}.input-field.svelte-18cwlk6:focus {outline:none;border-color:var(--color-primary);}.toggle-btn.svelte-18cwlk6 {position:absolute;right:12px;background:transparent;border:none;cursor:pointer;font-size:1.1rem;opacity:0.6;transition:opacity 0.2s;}.toggle-btn.svelte-18cwlk6:hover {opacity:1;}.toggle-card.svelte-18cwlk6 {margin-bottom:24px;padding:16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);}.toggle-header.svelte-18cwlk6 {display:flex;justify-content:space-between;align-items:center;}.toggle-label.svelte-18cwlk6 {margin:0;font-size:0.875rem;font-weight:600;}.switch.svelte-18cwlk6 {position:relative;width:44px;height:24px;background:rgba(255, 255, 255, 0.2);border-radius:999px;border:none;cursor:pointer;transition:background 0.2s;}.switch.active.svelte-18cwlk6 {background:var(--color-primary, #14b8a6);}.switch-thumb.svelte-18cwlk6 {position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:transform 0.2s;}.switch.active.svelte-18cwlk6 .switch-thumb:where(.svelte-18cwlk6) {transform:translateX(20px);}.warning-box.svelte-18cwlk6 {margin-top:12px;padding:8px 12px;background:rgba(245, 158, 11, 0.1);border:1px solid rgba(245, 158, 11, 0.2);border-radius:6px;font-size:11px;color:#fbbf24;line-height:1.4;}.feedback.svelte-18cwlk6 {margin-bottom:16px;padding:10px 14px;border-radius:var(--radius, 12px);font-size:0.875rem;}.feedback.error.svelte-18cwlk6 {background:rgba(239, 68, 68, 0.1);border:1px solid #ef4444;color:#ef4444;}.feedback.success.svelte-18cwlk6 {background:rgba(16, 185, 129, 0.1);border:1px solid #10b981;color:#10b981;}.actions.svelte-18cwlk6 {display:flex;justify-content:flex-end;}.btn-primary.svelte-18cwlk6 {padding:10px 24px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);font-weight:600;border:none;border-radius:var(--radius, 12px);cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-18cwlk6:hover:not(:disabled) {opacity:0.9;box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-18cwlk6:active:not(:disabled) {transform:scale(0.98);}.btn-primary.svelte-18cwlk6:disabled {opacity:0.5;cursor:not-allowed;}.mt-2.svelte-18cwlk6 {margin-top:8px;}"
};
function Bi(e, t) {
	We(t, !1), Ur(e, zi);
	let n = fi(t, "apiBase", 12, ""), r = /* @__PURE__ */ F(!0), i = /* @__PURE__ */ F(!1), a = /* @__PURE__ */ F(!1), o = /* @__PURE__ */ F(""), s = /* @__PURE__ */ F(""), c = /* @__PURE__ */ F(!1), l = /* @__PURE__ */ F(!1), u = /* @__PURE__ */ F(!1);
	Ar(async () => {
		await d(), I(r, !1);
	});
	async function d() {
		try {
			n();
			let e = await fetch(`${n()}/config`);
			if (e.ok) {
				let t = await e.json();
				I(c, t.token_configured ?? !1), I(u, t.auto_contribute ?? !1), Y(c) && I(s, "");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Failed to load config:", e);
		}
	}
	async function f() {
		let e = { auto_contribute: Y(u) };
		if (Y(s).trim()) e.user_token = Y(s).trim();
		else if (Y(u) && !Y(c)) {
			I(o, "A User Token is required to enable auto-contributions.");
			return;
		}
		I(o, ""), I(i, !0), I(a, !1);
		try {
			n();
			let t = await fetch(`${n()}/config`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			});
			if (t.ok) {
				let e = await t.json();
				I(c, e.token_configured ?? Y(c)), I(s, ""), I(a, !0), dispatchEvent(new CustomEvent("musicbrainz-config-saved", {
					bubbles: !0,
					composed: !0,
					detail: {
						auto_contribute: Y(u),
						token_configured: Y(c)
					}
				})), setTimeout(() => I(a, !1), 3e3);
			} else {
				let e = await t.json().catch(() => ({}));
				I(o, e.error || "Failed to save configuration.");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Save error:", e), I(o, "Network error while saving. Please try again.");
		} finally {
			I(i, !1);
		}
	}
	var p = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Ot();
		}
	};
	si();
	var m = Ri(), h = z(R(m), 2), g = (e) => {
		$(e, Mi());
	}, _ = (e) => {
		var t = Li(), n = z(en(t), 2), r = R(n), d = z(R(r)), p = (e) => {
			$(e, Ni());
		};
		Mr(d, (e) => {
			Y(c) && e(p);
		}), A(r);
		var m = z(r, 4), h = R(m);
		Zr(h);
		var g = z(h, 2), _ = tn(g, !0);
		A(m), A(n);
		var v = z(n, 2), y = R(v), b = z(R(y), 2);
		A(y);
		var x = z(y, 4), S = (e) => {
			$(e, Pi());
		};
		Mr(x, (e) => {
			Y(u) && !Y(c) && !Y(s) && e(S);
		}), A(v);
		var C = z(v, 2), w = (e) => {
			var t = Fi(), n = tn(t);
			xn(() => Sr(n, `⚠ ${Y(o) ?? ""}`)), $(e, t);
		};
		Mr(C, (e) => {
			Y(o) && e(w);
		});
		var ee = z(C, 2), te = (e) => {
			$(e, Ii());
		};
		Mr(ee, (e) => {
			Y(a) && e(te);
		});
		var ne = z(ee, 2), T = R(ne), E = tn(T, !0);
		A(ne), xn(() => {
			$r(h, "type", Y(l) ? "text" : "password"), $r(h, "placeholder", Y(c) ? "••••••••  (leave blank to keep current)" : "Enter your MusicBrainz user token"), $r(g, "title", Y(l) ? "Hide token" : "Show token"), $r(g, "aria-label", Y(l) ? "Hide token" : "Show token"), Sr(_, Y(l) ? "🙈" : "👁️"), $r(b, "aria-checked", Y(u)), Kr(b, 1, `switch ${Y(u) ? "active" : ""}`, "svelte-18cwlk6"), T.disabled = Y(i), Sr(E, Y(i) ? "Saving…" : "Save Settings");
		}), ri(h, () => Y(s), (e) => I(s, e)), Z("click", g, () => I(l, !Y(l))), Z("click", b, () => I(u, !Y(u))), Z("click", T, f), $(e, t);
	};
	return Mr(h, (e) => {
		Y(r) ? e(g) : e(_, -1);
	}), A(m), $(e, m), Ge(p);
}
customElements.define("musicbrainz-settings-card", vi(Bi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
